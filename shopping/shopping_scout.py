"""shopping — **기억하는 쇼핑 도우미**(Phase S).

쇼핑 검색은 세상에 많다. 이 에이전트가 만드는 것은 검색이 아니라 **기억**이다:
*"지난주에 망설이던 그 이어폰, 12,000원 내렸어요."*

## 어떻게 도나

1. 지난번에 이 물건을 어디까지 봤는지 **먼저 읽는다**(`shopping.recall_search`)
2. 웹에서 찾고, 모델이 그 결과를 **후보 정규형**으로 옮긴다
3. 이번 것을 **브레인에** 남긴다 — 에이전트 자체 저장소가 아니다
4. 지난번과 나란히 놓고(`compare_with_past`) **무엇이 달라졌는지** 말한다

## 말과 화면은 축이 다르다

★음성으로는 **상위 둘까지**만 말한다★ 목록을 읽어 주는 것은 도움이 아니라 소음이고,
사람은 넷째 항목쯤에서 앞을 잊는다. **비교는 화면이 한다**(`view()`).

★그리고 그 화면은 **선언 블록**으로 그린다★(2026-08-18에 되돌렸다)

AS-6에서 이 화면은 HTML을 통째로 만들어 액자(`iframe sandbox`)에 넣었다. Sean의
요구(*"모든 결과물은 html로 만들어서 새롭게 보여주길"*)를 그렇게 읽었는데, 요구의
목적은 *"HTML이라는 기술"* 이 아니라 **결과가 한 화면에서 읽히고 거기서 결정까지
가는 것**이었다. 그리고 그 목적을 위한 어휘는 **이미 있었다** — `compare`·
`price_history`는 계약에도 있고 셸도 그릴 줄 안다. 우리 것을 남의 방식으로 그리며
값을 셋 치렀다: 디자인 토큰이 안 닿고, 계측기가 못 찍고, 쪽 넘김이 어려웠다.

⚠️ `html` 블록을 **없앤 것이 아니다** — 마켓에서 받은 남의 에이전트는 우리 어휘
밖의 화면을 그려야 하고, 그때 격리가 필요하다. 쇼핑은 우리 것이라 우리 어휘로 그린다.

## 결제로 이어진다 — ★단, 마지막 버튼은 사람이 누른다★ (AS-7)

패널의 결제 단추는 **우리**를 부르고(`action="checkout"`), 우리가 브레인에 남긴 뒤
월렛에게 넘긴다. 월렛이 하는 일은 *"이 사이트의 폼을 채워도 될까요"* 라는 **요청**
이고, 승인과 마지막 버튼은 사람의 것이다(W5의 상한).

★액자가 월렛을 직접 부르지 않는 이유★ 그러면 그 결제가 **무엇에 대한 것인지**
브레인이 영영 모른다. 쇼핑을 지나야 *"지난번에 결제까지 갔던 그것"* 이 남는다.

## 판정은 코어가 한다

순위·가격 변동·신뢰 신호는 전부 `cosmos/core/shopping.py`에 있다. 여기서 다시
판정하면 **화면과 말이 서로 다른 것을 말하게 된다** — 연동 화면에서 이미 겪은 실패다.
"""
from __future__ import annotations

import json

import shopping_i18n as i18n
from cosmos.contracts import Plugin, ToolContext
from shopping_core import (
    Candidate, MAX_KEPT, MIGRATION_MARK_FILE, OUTCOMES, PAGE_SIZE, TRUST_SIGNALS,
    cheapest_index, compare_with_past, due_for_recheck, migrate_products_once,
    money, origin_of, page_of, rank, recall_search, remember_check,
    remember_checkout, remember_outcome, remember_search, signals_worth_showing,
    watchlist, worth_interrupting,
)

# 모델에게 주는 지시 — **정규형으로 옮기는 일만** 시킨다. 판정(순위·신뢰)을 맡기면
# 매번 다른 기준이 나오고, 그 기준을 아무도 설명할 수 없다.
_EXTRACT = (
    "You turn raw web search results into product candidates.\n"
    "Return ONLY a JSON array. Each item:\n"
    '{"title": str, "price": int (0 if unknown), "currency": "KRW"|"USD"|…,\n'
    ' "seller": str, "url": str, "signals": {"rating": float|null,\n'
    ' "review_count": int|null, "official_store": bool|null},\n'
    ' "image": str (https link to a photo OF THE PRODUCT, "" if the results do\n'
    '   not contain one -- ★never guess or build an image URL★, a made-up link\n'
    '   shows the user an empty box where the product should be),\n'
    ' "note": str (one short sentence on why this one is worth looking at)}\n'
    "★Never invent a price, rating or review count. Use null when unknown —\n"
    "a guessed number becomes a fact on the user's screen.★\n"
    f"At most {MAX_KEPT} items."
)


class ShoppingPlugin(Plugin):
    name = "shopping"
    version = "0.1.0"
    author = "cosmos"
    # 🛒 마켓에 실린다(A1). `view_title`은 **화면 제목**이고 이쪽은 **마켓 이름**이다.
    title = "Shopping scout"
    summary = ("Remembers what you were thinking of buying, then tells you when the "
               "price drops or a better option shows up. Compares choices on one "
               "screen with the reason spelled out.")
    category = "shopping"
    # ★왜 사용자가 이것을 들였나★(Phase AG) — `summary`가 *"무엇을 하는가"* 라면
    # 이 칸은 *"이 사람이 왜 이걸 갖고 있는가"* 다. 그것이 **무엇을 남길지**의
    # 기준이 된다(원칙 0 ①): 사려는 마음은 남고, 그때의 가격은 안 남는다.
    # ★순서가 있다★(Sean 결정 2026-08-18) — 값을 지켜보는 것이 **주**이고, 고를 때
    # 본 기준은 그 결정에 **딸린 부**다. 기준을 지속되는 취향으로 굳히면 안 되지만
    # (`Sean likes Price`), 그 물건을 다시 볼 때는 꺼내 줘야 한다.
    purpose = (
        "The user installed this because buying something well takes days -- they "
        "look, they wait, they compare -- and none of that survives the moment. "
        "First it keeps what they are still thinking of buying and what it cost, so "
        "it can say 'that one dropped'. Second, and only alongside that decision, it "
        "keeps what they weighed while choosing -- not as a lasting taste, but so the "
        "reasons come back when they look at that thing again."
    )
    # ★원하는 사람만 들인다★ — ③ 돈이 걸린다
    optional = True
    # ★값이 내리면 **먼저** 말한다★ (Sean 요구 2026-08-18) 화면을 열어야 보이는 것은
    # 절반만 만든 것이다 — 사려던 물건이 싸졌을 때 때를 놓치면 그 정보는 값이 없다.
    # 사용자가 이 훅을 끄면 `hooks.enabled()`가 먼저 걸러 `advise()`가 안 불린다.
    raises_notices = True
    # ★말로 이렇게 시킨다★ — 사용자가 이 카드에서 읽는 사용법이다
    howto = (
        "I am thinking about buying a standing desk",
        "Did anything I was watching get cheaper?",
        # ★카드의 사용법과 화면의 단추가 **같은 낱말**이다★ 다르면 사용자는 둘 중
        # 하나만 쓰게 되고, 번역도 두 벌이 된다.
        "Show the next ones",
    )
    description = ("Finds where to buy something safely, compares options with "
                   "reviews and prices, and remembers what you were looking at "
                   "so it can tell you when a price moves.")
    # ★`required`가 비어 있는 이유★ 이 도구는 두 가지 일을 한다 — 찾기와, 이미 찾아
    # 둔 것으로 넘어가기. `query`를 필수로 박아 두면 결제·열기 호출이 **선언을
    # 어기는 호출**이 된다(그리고 선언은 모델에게 거짓말이 된다). 무엇이 언제
    # 필요한지는 각 칸의 설명이 말한다.
    parameters = {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING",
                      "description": "What the user wants to buy, in their words. "
                                     "Needed to search."},
            "action": {"type": "STRING",
                       "description": "search (default) — look for it now. "
                                      "next — show the next few from the list already "
                                      "on screen (use this whenever the user asks to "
                                      "see more, the next ones, or others). "
                                      "prev — go back one page. "
                                      "checkout — start paying for one already found. "
                                      "open — open that one in the browser. "
                                      "bought — the user says they got it (stop watching "
                                      "the price and stop asking). "
                                      "dropped — the user says they are not buying it "
                                      "after all. "
                                      "still_looking — they have not bought it yet; undo "
                                      "either of those two."},
            "index": {"type": "INTEGER",
                      "description": "Which candidate from the last comparison "
                                     "(1 = the recommended one). For checkout and open."},
        },
        "required": [],
    }
    # ★`memory`가 있는 이유★ 쇼핑 의도를 **브레인에** 남긴다 — 에이전트 안에 두면
    # 다른 경로에서 "요즘 뭐 사려고 했지?"에 답할 수 없다.
    capabilities = ["network", "memory", "shopping.search"]
    requires_desktop = False
    view_title = "Shopping"

    # -- 도구 -----------------------------------------------------------------
    brain = {
        # ★"갖고 싶은 것"·"팔리는 물건"·"가진 것"을 **다른 kind로** 둔다★(Phase S·K2)
        # 한 kind에 넣으면 *"내가 뭘 갖고 있지?"* 에 사지도 않은 것이 섞인다.
        #
        # ★결제까지 간 것도 여기 남는다★(AS-7) 순간값(그때 가격)이 아니라 **나중에도
        # 참인 사실**이고, 다음 검색이 그것을 되읽어 *"샀나요?"* 라고 묻는다 —
        # `remember_checkout` → `recall_search` → `compare_with_past` → `_headlines`.
        "stores": ("wish", "product"),
        "reads": ("wish", "product"),
        # ⚠️ ★`preference`를 선언에서 뺐다★ (2026-08-18 실측) 적어 놓고 **한 번도
        # 쓰지 않았다** — 표에 있는데 아무도 안 채우면, 다음 사람은 있는 줄 알고
        # 배선했다가 영영 빈 값을 받는다(함정 74).
        #
        # ★그리고 그 자리를 야간 추출이 대신 채우고 있었다★ — 쇼핑 대화에서
        # `Sean likes Price` · `Delivery Reliability` · `Black`을 뽑아 **취향으로**
        # 굳혔다. 그것은 그때의 **판단 기준**이지 지속되는 취향이 아니다.
        # 실측으로 확인했다: 그 넷의 출처는 전부 `sleep.extract.v1`이고
        # 이 에이전트가 만든 것은 `product` 12 · `wish` 4뿐이다(선언 그대로).
        #
        # 고친 자리는 여기가 아니라 추출 프롬프트다(`memory_lite/extract.py`).
        # ★기준은 **결정에 붙어서** 산다★(Sean 결정 2026-08-18 — *"둘 다, 그런데
        # 순서가 있다"*) 지속되는 취향으로 굳히지 않는다 — 그것이 오늘 그래프를
        # 더럽힌 `Sean likes Price`였다. 대신 그 `wish`의 **속성**으로 남아, 같은
        # 물건을 다시 볼 때 *"저번엔 배송을 보셨죠"* 가 나온다.
        "settled": "What the person weighed while choosing one thing -- price, "
                   "delivery, seller reputation, a colour -- is never stored as a "
                   "lasting preference of theirs; that is how 'Sean likes Price' got "
                   "into the graph. It rides on the wish for that decision instead, "
                   "so the reasons come back with the thing and go when it goes.",
    }

    # ★액자가 부를 수 있는 일★ — 이 표가 곧 *"패널에서 무엇이 일어날 수 있는가"* 다
    # (원칙 1: 새 행동은 여기 한 줄이고, 없는 이름은 아무 일도 하지 않는다).
    _PANEL_ACTIONS = ("checkout", "open")

    # ★쪽 넘김은 **말로도 손으로도** 같은 문을 쓴다★ (Sean 요구 2026-08-18 —
    # *"다음 보기라고 말하면 다음의 리스트를 보여주도록"*)
    #
    # 버튼만 만들면 말로는 못 넘기고, 말만 만들면 손으로는 못 넘긴다. 그래서 둘 다
    # 이 표의 같은 이름으로 들어온다 — 화면의 단추도 `{"action": "next"}`를 보낸다.
    _PAGE_ACTIONS = ("next", "prev")

    # ★사람이 **말한 것**만 여기 들어온다★ 우리가 결제를 실행하지 않으므로 "샀다"는
    # 추측할 수 없다. 이 표가 없으면 *"샀나요?"* 를 물어 놓고 답을 버리게 된다.
    _OUTCOME_ACTIONS = tuple(OUTCOMES) + ("still_looking",)

    def __init__(self) -> None:
        # 이 과정에서 띄워 둔 알림 — 내릴 때 무엇을 내릴지 알아야 한다
        self._raised: set[str] = set()

    def run(self, ctx: ToolContext, **args) -> str:
        action = str(args.get("action") or "search").strip().lower()
        if action in self._PAGE_ACTIONS:
            return self._turn_page(ctx, action)
        if action in self._OUTCOME_ACTIONS:
            return self._settle(ctx, action, args.get("index"))
        if action in self._PANEL_ACTIONS:
            return self._from_panel(ctx, action, args.get("index"))
        query = str(args.get("query") or "").strip()
        if not query:
            return i18n.t("Tell me what to look for.")
        ctx.write_log(f"[shopping] {query}")

        brain, uid = ctx.brain, getattr(ctx, "user_id", "local")
        # ★옛 후보를 한 번 옮긴다★ 예전에는 `remember_search` 안에서 불렀는데, 표시를
        # 둘 자리(우리 폴더)를 아는 것은 **여기**뿐이다. 멱등이라 매번 불러도 된다.
        if brain is not None:
            try:
                migrate_products_once(brain, uid,
                                      ctx.data_dir(self.name) / MIGRATION_MARK_FILE)
            except Exception as e:
                ctx.write_log("[shopping] " + i18n.t(
                    "Could not tidy old candidates: {detail}", detail=e))
        past = recall_search(brain, uid, query) if brain else {}
        candidates = rank(self._find(ctx, query))
        if not candidates:
            # ★못 찾았으면 그렇다고 말한다★ 빈 목록에 그럴듯한 말을 붙이면
            # 사용자는 "그런 물건이 없다"로 읽는다.
            return i18n.t("I could not find '{query}'. Could you say it a little "
                          "differently?", query=query)

        if brain:
            # ★`self`를 넘긴다★(R4) 산출물이 **누가 찾아 온 것인지** 가리킨다.
            # 자기 서술(`title`·`summary`·`category`·`capabilities`)은 이미 이 클래스에
            # 선언돼 있으므로, 코어가 그것을 읽어 그래프에 세운다 — 새 에이전트가
            # 마켓에서 설치돼도 코드 수정이 0이다.
            remember_search(brain, uid, query, candidates, agent=self)
        diff = compare_with_past(past, candidates)
        self._remember_view(ctx, query, candidates, past, diff)
        return self._say(query, candidates, diff)

    def _find(self, ctx: ToolContext, query: str) -> list[Candidate]:
        """웹에서 찾아 **정규형으로** 옮긴다. 실패는 빈 목록이다(거짓말하지 않는다)."""
        try:
            # ★검색어도 언어를 탄다★ 한국어 낱말을 박아 두면 다른 언어 사용자는
            # 엉뚱한 결과를 받는다 — 표시문이 아니라 **기능**이 언어에 묶인 것이다.
            terms = i18n.t("buy price review")
            raw = ctx.run_tool("web_search", {"query": f"{query} {terms}"})
        except Exception as e:
            ctx.write_log("[shopping] " + i18n.t(
                "Search failed: {detail}", detail=e))
            return []
        if not raw or not str(raw).strip():
            return []
        try:
            text = ctx.think(f"{_EXTRACT}\n\n---\n{str(raw)[:6000]}", fast=True)
            rows = json.loads(_only_json(text))
        except Exception as e:
            ctx.write_log("[shopping] " + i18n.t(
                "Could not tidy the candidates: {detail}", detail=e))
            return []
        return [c for c in (_to_candidate(r) for r in rows if isinstance(r, dict)) if c]

    # -- 결제·열기 — ★액자가 보낸 것은 **번호뿐**이다★ ---------------------------
    def _turn_page(self, ctx: ToolContext, action: str) -> str:
        """*"다음 보기"* — 화면에 이미 펼쳐 둔 목록의 다음 넷.

        ★다시 검색하지 않는다★ 같은 말로 다시 찾으면 순위가 흔들려서 *"다음"* 인데
        아까 본 것이 또 나온다. 넘기는 것은 **이미 찾아 둔 목록** 안에서다.
        """
        state = _load(ctx)
        items = state.get("items") or []
        if not items:
            return i18n.t("There is no list open yet — tell me what to look for.")

        _, current, pages = page_of(items, state.get("page"))
        shown, page, _ = page_of(items, current + (1 if action == "next" else -1))
        if page == current:
            # ★끝은 끝이라고 말한다★ 되감아서 첫 쪽을 주면 사용자는 그것을 새 목록으로
            # 읽고, 같은 것을 두 번 검토한다.
            return self._notice(ctx, state, i18n.t(
                "That is the last of them.") if action == "next" else i18n.t(
                "This is already the first page."))

        state["page"] = page
        state.pop("notice", None)      # 지난 쪽에서 누른 단추의 소식은 여기 안 따라온다
        _save(ctx, state)
        first = page * PAGE_SIZE + 1
        return i18n.t("Numbers {first} to {last} of {total}, page {page} of {pages}.",
                      first=first, last=first + len(shown) - 1, total=len(items),
                      page=page + 1, pages=pages)

    # -- ★값이 내리면 먼저 말한다★ (Sean 요구 2026-08-18) --------------------
    def advise(self, ctx: ToolContext) -> None:
        """배경에서 지켜보다 **싸졌을 때** 알린다 — 그리고 해소되면 스스로 내린다.

        ## 왜 이 훅인가

        화면을 열어야 보이는 것은 절반만 만든 것이다. *"지난주에 망설이던 그것"* 이
        싸진 사실은 **때를 놓치면 값이 없다**(할인은 끝난다).

        ## ⚠️ 한 번에 **하나만** 본다

        `advise()`는 말이 오갈 때마다 불린다. 여기서 지켜보는 것을 전부 다시 검색하면
        대화 한 번에 웹 검색이 열 번 나간다. 그래서 **점검할 때가 된 것 하나**만
        고르고, 나머지는 다음 차례에 본다.

        ## 알림은 **상태**다

        같은 키로 다시 부르면 덮어쓴다. 사람이 *"샀어"* 라고 하면 그 물건은
        `watchlist`에서 빠지고, 그 순간 이 함수가 **알림을 내린다**(`clear`).
        내려가지 않는 알림은 두 번째부터 무시당한다.
        """
        brain = getattr(ctx, "brain", None)
        if brain is None or not callable(getattr(ctx, "notice", None)):
            return
        uid = getattr(ctx, "user_id", "local")
        try:
            watching = watchlist(brain, uid)
        except Exception:
            return

        # ★해소되면 스스로 내려간다★ 지켜볼 것에서 빠진 물건의 알림은 여기서 사라진다.
        open_keys = {self._notice_key(row["query"]) for row in watching}
        for key in list(self._raised - open_keys):
            self._clear(ctx, key)

        row = next((r for r in watching if due_for_recheck(r["last_checked"])), None)
        if row is None:
            return
        self._check_one(ctx, row)

    def _check_one(self, ctx: ToolContext, row: dict) -> None:
        """지켜보던 것 하나를 다시 보고, 말할 만하면 알린다."""
        brain, uid = ctx.brain, getattr(ctx, "user_id", "local")
        watching = row["watching"]
        try:
            fresh = rank(self._find(ctx, row["query"]))
        except Exception:
            return
        # ★같은 상품을 찾는다★ 다른 물건이 싸진 것을 "그게 싸졌다"고 말하면 거짓말이다
        same = next((c for c in fresh
                     if c.key() == Candidate(title=watching["title"]).key()), None)
        if same is None or not same.price:
            remember_check(brain, uid, row["wish_id"])
            return

        verdict = worth_interrupting(watching["price"], same.price,
                                     last_alert=row["last_alert"])
        if not verdict["tell"]:
            remember_check(brain, uid, row["wish_id"])
            return

        # ★새 값을 기억에 남긴다★ 안 남기면 다음번에 **같은 인하를 또** 알린다
        try:
            remember_search(brain, uid, row["query"], fresh, agent=self)
        except Exception:
            pass
        ctx.notice(
            self._notice_key(row["query"]),
            # ★말로 나가는 줄이다★ 읽는 글이 아니라 **하는 말**로 쓴다
            i18n.t("{title} is {amount} cheaper than when you looked.",
                   title=same.title,
                   amount=money(abs(verdict["delta"]), same.currency)),
            level="warn",
            detail=i18n.t("Now {price} at {seller}.",
                          price=money(same.price, same.currency),
                          seller=same.seller or i18n.t("the shop")),
            action={"label": i18n.t("Show me"), "tool": self.name,
                    "args": {"query": row["query"]}})
        self._raised.add(self._notice_key(row["query"]))
        remember_check(brain, uid, row["wish_id"], alerted=True)

    @staticmethod
    def _notice_key(query: str) -> str:
        """★의도마다 하나★ 상품마다 키를 만들면 한 물건으로 알림이 넷 뜬다."""
        return "price:" + str(query or "")[:80]

    def _clear(self, ctx: ToolContext, key: str) -> None:
        try:
            ctx.clear_notice(key)
        except Exception:
            pass
        self._raised.discard(key)

    # -- ★"샀어" · "안 살래" 를 적는다★ ---------------------------------------
    def _settle(self, ctx: ToolContext, action: str, index) -> str:
        """*"샀나요?"* 의 답을 남긴다.

        ★안 적으면 열 번을 물어도 매번 처음이다★ 그리고 무엇보다 **산 사람에게도
        "더 싸졌어요"라고 말하게 된다** — 도움이 아니라 상처다.
        """
        state = _load(ctx)
        items = state.get("items") or []
        try:
            position = int(index or 1)
        except (TypeError, ValueError):
            position = 1
        if not (1 <= position <= len(items)):
            position = 1
        if not items:
            return i18n.t("Which one? Search for it and I will line them up.")
        title = str(items[position - 1].get("title") or "")
        outcome = "" if action == "still_looking" else action

        brain = getattr(ctx, "brain", None)
        if brain is None or not state.get("query"):
            return i18n.t("I could not write that down.")
        try:
            remember_outcome(brain, getattr(ctx, "user_id", "local"),
                             state["query"], title, outcome)
        except Exception as e:
            ctx.write_log("[shopping] " + i18n.t(
                "Could not write down what you decided: {detail}", detail=e))
            return i18n.t("I could not write that down.")
        # 지켜보기를 그만두는 순간 알림도 내려간다(해소되면 사라진다)
        if outcome:
            self._clear(ctx, self._notice_key(state["query"]))
        if action == "bought":
            return self._notice(ctx, state, i18n.t(
                "Got it -- {title} is yours. I will stop watching that price.",
                title=title))
        if action == "dropped":
            return self._notice(ctx, state, i18n.t(
                "Alright, I will stop bringing up {title}.", title=title))
        return self._notice(ctx, state, i18n.t(
            "Noted -- still looking at {title}.", title=title))

    def _from_panel(self, ctx: ToolContext, action: str, index) -> str:
        """패널 단추에서 온 호출. 주소·상품명은 **우리 상태에서** 꺼낸다.

        ★번호만 받는 이유★ 액자가 주소를 실어 보내면, 오염된 액자가 자기 주소로
        결제 승인을 띄울 수 있다. 번호는 *"우리가 이미 찾아 둔 것 중 몇 번째"* 밖에
        고르지 못한다 — 최악의 경우에도 우리가 찾아 온 상점을 벗어나지 않는다.
        """
        state = _load(ctx)
        items = state.get("items") or []
        try:
            position = int(index or 0)
        except (TypeError, ValueError):
            position = 0
        if not (1 <= position <= len(items)):
            # ★없는 번호를 조용히 첫 번째로 바꾸지 않는다★ 결제 대상이 미끄러지는 것은
            # 가장 나쁜 종류의 친절이다.
            return self._notice(ctx, state, i18n.t(
                "I lost track of that one — search again and I will line them up."))
        item = items[position - 1]
        url = str(item.get("url") or "")
        if not url:
            return self._notice(ctx, state, i18n.t(
                "I do not have a link for {title}.", title=item.get("title", "")))
        if action == "open":
            ctx.run_tool("browser_control", {"url": url})
            return self._notice(ctx, state, i18n.t("Opened {title}.",
                                                   title=item.get("title", "")))

        # ★기억이 먼저다★ 월렛에 넘기고 나서 남기면, 월렛이 거절했을 때는 아무 흔적도
        # 안 남는다 — 그런데 *"결제하려 했다"* 는 거절당해도 참인 사실이다.
        if (brain := ctx.brain) is not None and state.get("query"):
            try:
                remember_checkout(brain, getattr(ctx, "user_id", "local"),
                                  state["query"], str(item.get("title") or ""),
                                  origin_of(url), agent=self)
            except Exception as e:
                ctx.write_log("[shopping] " + i18n.t(
                    "Could not remember the checkout: {detail}", detail=e))
        # 월렛이 하는 일은 **요청**이다 — 승인도 마지막 버튼도 사람의 것이다(W5).
        # ★값을 함께 넘긴다★ 승인의 한도(`per_approval`·`per_day`)는 금액 위에서만
        # 성립한다 — 우리가 아는 값을 안 넘기면 사용자가 그것을 손으로 다시 적어야 하고,
        # 손으로 적는 값은 화면에 보이는 가격과 어긋날 수 있다.
        return self._notice(ctx, state,
                            str(ctx.run_tool("wallet", {"action": "checkout",
                                                        "url": url,
                                                        "amount": item.get("price") or 0,
                                                        "currency": item.get("currency")
                                                        or "KRW"})))

    def _notice(self, ctx: ToolContext, state: dict, text: str) -> str:
        """★결과를 **상태에 적는다**★(착수 전 점검 구멍 3)

        `run_agent_action`은 도구를 실행한 뒤 **새 뷰를 그린다** — 그러면 액자가
        통째로 교체되고, 답 메시지는 그 뒤에 **죽은 창**으로 간다. 눌렀는데 아무 일도
        안 난 것처럼 보이는 것이다. 그래서 다음 `view()`가 그리도록 여기 적는다.
        """
        state["notice"] = text
        try:
            _save(ctx, state)
        except Exception:
            pass                    # 못 적어도 도구의 반환값은 모델에게 간다
        return text

    # -- 화면 -----------------------------------------------------------------
    def view(self, ctx: ToolContext, **params) -> dict:
        """★비교는 여기서 한다★ 말로는 둘까지, 나머지는 이 화면이 보여준다.

        ## ★액자를 떠나 **선언 블록**으로 돌아왔다★ (Sean 물음 2026-08-18)

        예전에는 표·도식·추천을 한 덩어리 HTML로 만들어 액자(`iframe sandbox`)에
        넣었다. 자유롭긴 했지만 대가가 셋이었다:

        | 대가 | 무슨 일이 났나 |
        |---|---|
        | **디자인 토큰이 안 닿는다** | 액자 안은 다른 문서다 — 색을 손으로 다시 적었다 |
        | **찍을 수 없다** | 계측기가 액자 속을 못 봐서 *"화면이 섰다"* 를 못 잰다 |
        | **페이지 넘김이 어렵다** | 액자가 바깥에 말을 걸어야 한 쪽 넘어간다 |

        그런데 이 화면이 그리는 것은 **우리가 아는 모양**이었다 — 나란히 비교
        (`compare`)와 가격 흐름(`price_history`)은 어휘에 **이미 있었고**, 셸도
        그릴 줄 알았다. 우리 것을 남의 방식으로 그리고 있었던 셈이다.

        ⚠️ ★액자를 없앤 것이 아니다★ `html` 블록은 그대로 있고, **마켓에서 받은
        남의 에이전트**가 자기 화면을 그릴 때 그 길을 쓴다. 우리 어휘로 표현되는
        것을 우리가 굳이 액자에 넣지 않을 뿐이다.
        """
        state = _load(ctx)
        if not state:
            return {"title": self.view_title,
                    "blocks": [{"type": "text", "tone": "muted",
                                "text": i18n.t(
                                    "What shall I look for? Ask me out loud and I "
                                    "will compare the options here.")}]}

        blocks: list[dict] = []
        diff = state.get("diff") or {}
        # ★지난번 이야기가 **맨 위에** 온다★ 이것이 이 에이전트의 값어치다
        for line in _headlines(diff):
            blocks.append({"type": "text", "tone": line["tone"], "text": line["text"]})

        items = state.get("items") or []
        shown, page, pages = page_of(items, state.get("page"))
        # ★번호는 **전체에서 몇 번째**다★ 쪽마다 1번부터 세면 3쪽의 1번을 결제했을 때
        # 1쪽의 1번이 결제된다 — 결제 대상이 미끄러지는 것은 가장 나쁜 종류의 사고다.
        base = page * PAGE_SIZE

        blocks.append({"type": "group", "icon": "🛒",
                       "label": state.get("query", ""),
                       # 몇 쪽 중 몇 쪽인지 — 없으면 사용자는 이게 전부라고 읽는다.
                       # ★낱말이 없는 서식은 번역하지 않는다★ 자리표시자뿐인 항목은
                       # 어느 언어에서도 원문과 같아서 "번역을 잊은 것"과 구별되지 않는다.
                       "action": {"label": f"{page + 1} / {pages}"} if pages > 1 else None})

        # ★미는 것은 **카드 위에** 붙인다★ 예전에는 위에 따로 한 줄을 두었는데,
        # 화면이 값으로 고른 카드에 테두리를 쳐서 **둘이 서로 다른 카드**를 가리켰다
        # (찍어 보고 알았다). 이제 추천은 그 카드가 직접 말한다.
        #
        # ⚠️ ★첫 쪽에서만이다★ 2쪽에서도 1위를 표시하면 **화면에 없는 것을 가리키는
        # 하이라이트**가 되고, 사용자는 *"왜 여기 없는 게 추천이지"* 에서 멈춘다.
        # (그물이 이것을 잡았다 — `test_saying_show_the_next_ones_moves_the_screen`)
        # ★"가장 싸다"도 **전체에서** 정한다★ 화면이 받은 넷에서 고르면 다음 쪽에
        # 더 싼 것이 있을 때 그 글자가 거짓말이 된다(2쪽을 찍어 보고 알았다).
        low = cheapest_index(items)
        blocks.append({"type": "compare",
                       # ★아무도 모르는 신호는 칸을 안 만든다★(코어의 순수 함수)
                       "signals": signals_worth_showing(shown),
                       "items": [self._card(item, base + n, lead=(base + n == 0),
                                            low=(base + n == low))
                                 for n, item in enumerate(shown)]})

        if history := (state.get("history") or []):
            blocks.append({"type": "price_history", "items": history,
                           "label": i18n.t("Price trend")})

        if buttons := self._nav(items, page, pages):
            blocks.append({"type": "actions", "items": buttons})

        # ★단추를 누른 결과는 화면이 다시 그려진 **뒤에** 보여야 한다★(구멍 3)
        if notice := state.get("notice"):
            blocks.append({"type": "text", "tone": "info", "text": str(notice)})
        return {"title": self.view_title, "blocks": blocks,
                "params": {"query": state.get("query", ""), "page": page}}

    def _card(self, item: dict, position: int, *,
              lead: bool = False, low: bool = False) -> dict:
        """후보 하나를 비교 카드로. `position`은 **0부터 세는 전체 순번**이다.

        ★배지는 하나만 단다★ 1위가 마침 가장 싸기도 하면 *"추천"* 이 이긴다 —
        둘을 나란히 붙이면 배지가 정보가 아니라 장식이 된다.
        """
        return {"title": item.get("title", ""), "seller": item.get("seller", ""),
                "price": item.get("price"), "currency": item.get("currency"),
                "seen_at": item.get("seen_at", ""), "note": item.get("note", ""),
                "mark": i18n.t("Best pick") if lead else (i18n.t("Cheapest") if low else ""),
                "lead": lead, "image": item.get("image", ""),
                "affiliate": bool(item.get("affiliate")),
                "signals": dict(item.get("signals") or {}),
                # ★단추는 **번호만** 보낸다★ 주소를 실어 보내면 오염된 화면이 자기
                # 주소로 결제를 띄울 수 있다(`_from_panel`의 규칙 그대로).
                "action": {"label": i18n.t("Go and look"), "tool": self.name,
                           "args": {"action": "open", "index": position + 1}}
                if item.get("url") else None}

    def _nav(self, items: list, page: int, pages: int) -> list[dict]:
        """아래 단추 줄 — 결제 하나와 쪽 넘김 둘. ★순서가 곧 중요도다★"""
        out: list[dict] = []
        if page == 0 and items and items[0].get("url"):
            # 결제는 **1위 하나**에만 붙인다. 넷에 다 붙이면 "고르는 화면"이
            # "사는 화면"이 되고, 그때 비교는 장식이 된다.
            # 그리고 **그 1위가 보이는 쪽에서만** 붙인다 — 안 보이는 것을 사는
            # 단추는 무엇을 사는지 모르는 채 누르는 단추다.
            out.append({"label": i18n.t("Help me buy the best pick"),
                        "tool": self.name, "style": "primary",
                        "args": {"action": "checkout", "index": 1}})
        if page > 0:
            out.append({"label": "◀ " + i18n.t("Previous"), "tool": self.name,
                        "args": {"action": "prev"}})
        if page + 1 < pages:
            # ★말로 하는 것과 **같은 이름**★ 버튼에 "다음"이라 써 놓고 말로는
            # 다른 낱말을 받으면, 사용자는 둘 중 하나를 못 쓴다.
            out.append({"label": i18n.t("Show the next ones") + " ▶",
                        "tool": self.name, "args": {"action": "next"}})
        return out

    # -- 화면이 읽을 것을 남긴다 ----------------------------------------------
    def _remember_view(self, ctx: ToolContext, query: str,
                       candidates: list[Candidate], past: dict, diff: dict) -> None:
        """★도구와 화면이 **같은 것**을 본다★ 화면이 다시 검색하면 두 번 돈다."""
        history = []
        for old in (past.get("candidates") or []):
            if old.get("price") and old.get("seen_at"):
                history.append({"ts": old["seen_at"], "price": old["price"]})
        for c in candidates:
            if c.price and c.seen_at:
                history.append({"ts": c.seen_at, "price": c.price})
        history.sort(key=lambda p: p["ts"])
        try:
            # ★주소를 **여기** 둔다★ 화면의 단추는 번호만 보내므로(구멍 2), 번호를
            # 주소로 바꾸는 표가 우리 쪽에 있어야 한다. 화면으로는 안 내려간다 —
            # `_card()`에서 `url`은 "단추를 그릴까" 판단에만 쓰인다.
            _save(ctx, {
                # ★새 검색은 **첫 쪽부터**★ 3쪽을 보던 중에 다른 것을 찾으면, 쪽수가
                # 남아 있어 새 목록의 9번째부터 보인다(그리고 그것은 고장으로 읽힌다).
                "query": query, "diff": diff, "history": history[-30:], "page": 0,
                "items": [{"title": c.title, "price": c.price, "currency": c.currency,
                           "seller": c.seller, "note": c.note, "seen_at": c.seen_at,
                           "affiliate": c.affiliate, "signals": dict(c.signals or {}),
                           "url": c.url, "image": c.image}
                          for c in candidates]})
        except Exception as e:
            ctx.write_log("[shopping] " + i18n.t(
                "Could not save the screen state: {detail}", detail=e))

    def _say(self, query: str, candidates: list[Candidate], diff: dict) -> str:
        """★음성은 짧아야 한다★ 목록을 읽어 주면 사람은 넷째쯤에서 앞을 잊는다."""
        lines = [h["text"] for h in _headlines(diff)]
        top = candidates[:2]
        for c in top:
            # ★서식은 **코어의 함수 하나**가 한다★ 예전에는 이 자리와 화면 쪽에 같은
            # 규칙이 따로 적혀 있었고, 그래서 한쪽만 고치면 말과 화면이 갈렸다.
            where = f", {c.seller}" if c.seller else ""
            lines.append(f"{c.title} {money(c.price, c.currency)}{where}")
        if len(candidates) > len(top):
            lines.append(i18n.t("I lined up {count} of them on the screen.",
                                count=len(candidates)))
        # ★더 있다는 것을 **말해 줘야** 넘긴다★ 화면 단추만 두면 말로 쓰는 사람은
        # 뒤 페이지가 있는 줄도 모르고, 마음에 안 들면 같은 검색을 다시 한다.
        if len(candidates) > PAGE_SIZE:
            lines.append(i18n.t("Say 'show the next ones' for more."))
        return "\n".join(lines) if lines else i18n.t(
            "I tidied the results for '{query}' onto the screen.", query=query)


def _headlines(diff: dict) -> list[dict]:
    """지난번과 견줘 **말할 만한 것**만. 없으면 빈 목록이다."""
    if not diff or diff.get("first_time") or diff.get("stale"):
        return []
    out = []
    for change in (diff.get("changes") or [])[:2]:
        won = abs(change["delta"])
        if change["direction"] == "down":
            out.append({"tone": "good",
                        "text": i18n.t(
                            "{title}, which you were looking at last time, went down "
                            "by {amount}.", title=change["title"], amount=f"{won:,}")})
        else:
            out.append({"tone": "warn",
                        "text": i18n.t("{title} went up by {amount}.",
                                       title=change["title"], amount=f"{won:,}")})
    for title in (diff.get("gone") or [])[:1]:
        out.append({"tone": "muted",
                    "text": i18n.t("{title} is not showing up right now.",
                                   title=title)})
    # ★결제까지 갔던 것은 **묻는다**★(원칙 0 ③ · Phase S의 규칙 그대로)
    # 코어는 *"갔다"* 라는 사실만 주고, *"샀나요?"* 라는 물음은 여기서 만든다 —
    # 우리가 결제를 실행하지 않는 한 샀는지는 알 수 없고, 추측하면 그것이 오염이다.
    for row in (diff.get("checked_out") or [])[:1]:
        out.append({"tone": "info",
                    "text": i18n.t("Last time you went to checkout for {title}. "
                                   "Did you get it?", title=row.get("title", ""))})
    return out


def _to_candidate(row: dict) -> Candidate | None:
    from cosmos.contracts.memory import now_ts
    title = str(row.get("title") or "").strip()
    if not title:
        return None
    signals = {k: v for k, v in (row.get("signals") or {}).items()
               if k in TRUST_SIGNALS and v is not None}
    try:
        price = max(0, int(row.get("price") or 0))
    except (TypeError, ValueError):
        price = 0
    return Candidate(
        title=title[:120], price=price,
        currency=str(row.get("currency") or "KRW")[:8],
        seller=str(row.get("seller") or "")[:60],
        url=str(row.get("url") or "")[:500],
        image=str(row.get("image") or "")[:400],
        signals=signals, note=str(row.get("note") or "")[:200],
        # ★언제 잰 값인지 **여기서** 붙인다★ 모델이 준 시각을 믿으면 지어낸 값이 섞인다
        seen_at=now_ts())


def _only_json(text: str) -> str:
    """모델이 앞뒤로 말을 붙여도 배열만 꺼낸다."""
    body = str(text or "").strip()
    start, end = body.find("["), body.rfind("]")
    return body[start:end + 1] if 0 <= start < end else "[]"


# 화면이 읽을 것을 두는 자리. ★코드가 아니라 **상태**의 자리다★ — `data_dir`가
# 그 둘을 갈라 두므로 에이전트를 업데이트해도 진도가 지워지지 않는다.
_STATE_FILE = "last_search.json"


def _save(ctx: ToolContext, state: dict) -> None:
    (ctx.data_dir("shopping") / _STATE_FILE).write_text(
        json.dumps(state, ensure_ascii=False), encoding="utf-8")


def _load(ctx: ToolContext) -> dict:
    """읽지 못하면 **빈 상태**다 — 화면은 빈 것도 그릴 수 있어야 한다(M-H20)."""
    try:
        path = ctx.data_dir("shopping") / _STATE_FILE
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}
