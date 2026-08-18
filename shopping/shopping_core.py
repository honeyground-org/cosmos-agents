"""쇼핑 — **기억하는 쇼핑 도우미**의 코어(Phase S).

## 왜 이 파일이 있나

쇼핑 검색은 세상에 많다. **우리가 만드는 것은 검색이 아니다**:

| 보통의 쇼핑 검색 | 우리가 만드는 것 |
|---|---|
| 매번 처음부터 | ★지난번에 뭘 보다 말았는지 **기억한다**★ |
| 결과 목록 | **왜 이걸 권하는지**와 **어디가 믿을 만한지** |
| 지금 가격 | **그때 그 가격에서 얼마나 움직였는지** |

*"지난주에 망설이던 그 이어폰, 12,000원 내렸어요"* — 이것이 만들려는 것이고,
그것은 **기억 위에서만** 성립한다.

## ★의도는 브레인에 저장한다 — 에이전트 안에 두지 않는다★

이게 이 파일의 가장 중요한 결정이다. 쇼핑 이력을 에이전트의 자체 저장소에 두면
**브레인이 그것을 모른다**. 그러면 *"요즘 뭐 사려고 했지?"* 에 답할 수 없고,
다른 에이전트도 그 사실을 쓸 수 없다. 기억은 한 곳에 모여야 기억이다.

그래서 그래프에 이렇게 남는다:

    [무선 이어폰(wish)] --considering--> [소니 WF-1000XM5(item)]
                                    \\--> [젠하이저 모멘텀(item)]

## 신뢰는 **점수가 아니라 신호**다

*"이 판매처는 87점"* 은 그럴듯하지만 **근거가 없으면 거짓말**이다. 우리는 점수를
만들지 않고 관찰한 신호를 그대로 보여준다. 모르는 신호는 **"모름"** 이라고 쓴다 —
빈칸을 좋게 보이게 채우면 그 순간 이 기능은 광고가 된다.

## 가격에는 **잰 시각**이 붙는다

낡은 가격을 지금 가격처럼 보여주면 신뢰가 한 번에 깨진다. 그래서 `seen_at`이
정규형의 1급 칸이고, 화면은 그것을 **반드시** 말한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from cosmos.contracts.memory import (Entity, MemoryItem, Relation, Trust,
                                     entity_links, now_ts)
from cosmos.core import provenance

# 이 채널이 만든 것은 채널 단위로 걷어낼 수 있다(모든 자동 산출물의 규칙, D1b-4).
CHANNEL = "shopping.search.v1"

# 기억에 남는 종류 — 대화(`turn`)·가져온 것(`imported`)과 갈라 둔다.
ITEM_KIND = "shopping"

# ★후보의 kind — 소유물(`item`)이 **아니다**★(K2-0 · 실측으로 드러난 결함)
#
# 원래 이 자리가 `"item"`이었다. 온톨로지가 *"같은 kind에 넣으면 「내가 뭘 갖고
# 있지?」에 사지도 않은 게 섞인다"* 고 정확히 경고했는데, 그물이 **의도 이름**
# (*"무선 이어폰"*)만 검사하는 바람에 정작 **후보 상품**(*"소니 WF-1000XM5"*)이
# 소유물로 들어가는 것을 두 달간 아무도 못 봤다.
#
# 그리고 이것을 고치지 않으면 K2가 성립하지 않는다: "샀다"를 적으려면 `item`이
# **산 것만** 담고 있어야 하는데, 이미 후보로 차 있으면 둘을 구별할 방법이 없다.
PRODUCT_KIND = "product"

# 이미 `item`으로 저장된 옛 후보를 옮겼다는 표시의 파일 이름(★불변 규칙:
# 마이그레이션 없이 스키마 변경 금지★). 자리는 이 에이전트의 `data_dir`이다.
MIGRATION_MARK_FILE = "migrated.item-to-product"


def origin_of(url: str) -> str:
    """주소에서 **오리진만** 남긴다 — 결제 기록에 실리는 것은 이것이다. ★순수 함수★

    경로·질의는 버린다: 같은 상점의 다른 페이지는 같은 곳이다. 반대로 **호스트가
    다르면 다른 곳**이고, 거기가 정확히 피싱이 서는 자리다.

    ★`https`만 인정한다★ 평문으로 가는 폼은 그 자체가 유출이다. 아니면 빈 문자열을
    돌려준다 — 지어내면 기억에 **틀린 상점**이 남는다.
    """
    import urllib.parse
    parts = urllib.parse.urlsplit(str(url or "").strip())
    if parts.scheme != "https" or not parts.hostname:
        return ""
    host = parts.hostname.lower()
    return f"{host}:{parts.port}" if parts.port not in (None, 443) else host

# ★신뢰 신호의 주인은 **화면 계약**이다★ 이 에이전트가 어휘를 지어내면 화면이
# 무엇을 그릴지 모르게 되고, 그 순간 "비교가 한눈에"가 깨진다. 새 신호가 필요하면
# 코스모스의 `contracts/view.py`에 한 줄을 더한다(그리고 번역 다섯이 함께 온다).
from cosmos.contracts.view import COMPARE_SIGNALS as TRUST_SIGNALS

# 한 번에 보여줄 후보 수. ★목록이 길수록 좋은 것이 아니다★ — 스크롤해야 비교가
# 되면 "한눈에 결정"이 깨진다(S§2-5의 첫 번째 원칙).
PAGE_SIZE = 4

# ★그런데 넷이 **전부**는 아니다★ (Sean 요구 2026-08-18 — *"다음 보기라고 말하면
# 다음의 리스트를 보여주도록 페이지네이션도 한다"*)
#
# 예전에는 넷만 남기고 나머지를 **버렸다**. 그래서 *"다음 보기"* 라고 말할 것이
# 애초에 없었고, 마음에 드는 게 없으면 사용자가 **같은 검색을 다시** 해야 했다.
# 위의 원칙은 *"한 화면에 넷"* 이지 *"세상에 넷"* 이 아니다 — 넷씩 **넘겨** 보는
# 것은 그 원칙을 어기지 않는다(스크롤은 비교를 깨지만 페이지는 안 깬다).
#
# ⚠️ 뒤 페이지는 **화면 상태에만** 산다. 브레인에는 첫 페이지만 남긴다 — 사용자가
# 실제로 견준 것이 그것이고, 열두 개를 다 남기면 한 번 검색할 때마다 상품 노드가
# 열둘씩 늘어난다(원칙 0 ②: 아무거나 쌓지 않는다).
MAX_KEPT = PAGE_SIZE * 3

# 가격이 이만큼 움직여야 "변했다"고 말한다. 100원 차이를 알리면 그것은 소음이다.
PRICE_CHANGE_MIN_RATIO = 0.02


@dataclass
class Candidate:
    """상품 후보 하나 — 소스가 뭐든 **이 모양**으로 들어온다.

    `signals`가 dict인 이유: 소스마다 알 수 있는 것이 다르고, **모르는 것은 빈칸으로
    둬야** 하기 때문이다. 필드로 못 박으면 모르는 신호에 기본값이 들어가고,
    그 기본값이 화면에서 사실처럼 보인다.
    """

    title: str
    price: int = 0                   # 최소 화폐 단위(원). 0 = 모름
    currency: str = "KRW"
    seller: str = ""
    url: str = ""
    signals: dict = field(default_factory=dict)   # TRUST_SIGNALS의 키만 뜻을 갖는다
    affiliate: bool = False          # ★수수료가 걸렸는가 — 숨기지 않는다★
    seen_at: str = ""                # ★언제 잰 값인가 — 화면이 반드시 말한다★
    note: str = ""                   # 왜 이걸 권하는지(한 문장)
    # ★물건을 고르는 화면에서 사진은 장식이 아니라 정보다★(Sean 지적 2026-08-18)
    # 판매처의 주소를 그대로 쓴다. `https:`가 아니면 화면이 버린다(계약의 `_image`).
    image: str = ""

    def key(self) -> str:
        """같은 상품인가를 가르는 키. 판매처가 달라도 **상품이 같으면 같다** —
        그래야 "여러 곳에서 파는 하나"로 묶인다."""
        return _normalise_title(self.title)


def _normalise_title(title: str) -> str:
    """상품명을 비교 가능한 모양으로. 판매처마다 제목에 온갖 수식이 붙는다
    ("[무료배송] 소니 WF-1000XM5 정품 ★당일발송★")."""
    import re
    text = str(title or "").lower()
    text = re.sub(r"[\[\(【][^\]\)】]*[\]\)】]", " ", text)   # 대괄호 홍보 문구
    text = re.sub(r"[★☆♥●■▶]+", " ", text)
    text = re.sub(r"\b(무료배송|정품|당일발송|최저가|특가|free\s*shipping)\b", " ", text)
    text = re.sub(r"[^0-9a-z가-힣]+", " ", text)
    return " ".join(text.split())[:120]


def visible_signals(candidate: Candidate) -> list[dict]:
    """화면이 그리는 신호 목록 — **모르는 것은 "모름"으로 나온다**.

    빠뜨리지 않고 전부 돌려주는 것이 요점이다. 있는 것만 그리면 빈칸이 되고,
    빈칸은 **"없다"로 읽힌다**(그리고 그것이 거짓말이 된다).
    """
    rows = []
    for key, spec in TRUST_SIGNALS.items():
        raw = (candidate.signals or {}).get(key)
        rows.append({"key": key, "label": spec["label"],
                     "value": raw, "known": raw is not None})
    return rows


def price_change(before: int, after: int) -> dict:
    """가격이 얼마나 움직였나 — **말할 만한 변화인지**까지 판정한다.

    작은 흔들림까지 알리면 그것은 소음이고, 소음이 쌓이면 사람은 알림을 끈다.
    """
    if not before or not after:
        return {"changed": False, "delta": 0, "ratio": 0.0, "direction": ""}
    delta = after - before
    ratio = abs(delta) / before
    return {"changed": ratio >= PRICE_CHANGE_MIN_RATIO,
            "delta": delta, "ratio": round(ratio, 4),
            "direction": "down" if delta < 0 else ("up" if delta > 0 else "")}


def rank(candidates: list[Candidate]) -> list[Candidate]:
    """보여줄 순서 — ★수수료는 **반영하지 않는다**★

    수수료를 받는 곳을 "믿을 만한 곳"이라며 위에 올리면 이 기능의 목적이 뒤집힌다.
    정렬 근거는 **가격과 평점**뿐이고, 수수료 여부는 **화면에 표시만** 된다.
    이 규칙은 문서가 아니라 그물이 지킨다(`tests/test_shopping.py`).
    """
    def score(c: Candidate) -> tuple:
        rating = float((c.signals or {}).get("rating") or 0)
        # 가격을 모르면 뒤로 — 비교할 수 없는 것을 앞에 두면 비교가 안 된다
        price = c.price if c.price else 10 ** 12
        return (-round(rating, 1), price, c.title)
    return sorted(candidates, key=score)[:MAX_KEPT]


def page_of(items: list, page: int = 0, size: int = PAGE_SIZE) -> tuple[list, int, int]:
    """지금 쪽 · 몇 쪽째인가 · 모두 몇 쪽인가. ★순수 함수★

    ★끝에서 첫 쪽으로 **되감지 않는다**★ — 되감으면 사용자는 *"다음"* 을 눌렀는데
    처음 것이 나와서 새 목록으로 읽는다. 끝은 끝이라고 말해야 다음 행동을 고른다.

    빈 목록도 한 쪽이다(0쪽이면 *"1/0"* 같은 말이 나온다).
    """
    size = max(1, int(size))
    pages = max(1, -(-len(items) // size))          # 올림 나눗셈
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 0
    page = max(0, min(page, pages - 1))
    return items[page * size:(page + 1) * size], page, pages


def cheapest_index(items: list[dict]) -> int:
    """값을 아는 것 중 **가장 싼 것**이 전체에서 몇 번째인가(없으면 -1). ★순수 함수★

    ★한 쪽만 보고 정하면 거짓말이 된다★ 화면은 넷씩 받는데, 그 넷에서 가장 싼 것에
    *"최저가"* 를 달았더니 다음 쪽에 더 싼 것이 있었다(찍어 보고 알았다). 전체를 아는
    쪽이 판정한다 — 이 파일의 규칙 그대로다.

    값이 같은 것이 둘이면 **앞의 것**이다(순위가 이미 정렬해 두었다).
    """
    best, at = 0, -1
    for n, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        try:
            price = int(item.get("price") or 0)
        except (TypeError, ValueError):
            continue
        if price > 0 and (at < 0 or price < best):
            best, at = price, n
    return at


def money(price, currency: str = "KRW") -> str:
    """★통화는 상품이 정한다★ 예전에 '원'이 코드에 박혀 있어 달러로 파는 물건도
    원으로 읽혔다. 통화 이름은 번역하지 않는다 — 'KRW'는 어느 언어에서도 KRW다.

    ⚠️ 자릿점·기호의 **지역 규칙**(₩289,000 vs 289.000 ₩)은 별개 관심사이고
    아직 없다(셸의 `fmtPrice`와 같은 상태 — 두 곳이 같은 만큼만 한다).

    ★말과 화면이 **같은 함수**를 쓴다★ 예전에는 이 서식이 화면 쪽(`shopping_html`)과
    말하는 쪽(`_say`)에 따로 적혀 있었고, 그래서 한쪽만 고치면 *"화면은 289,000
    KRW인데 말로는 289000원"* 이 됐다.
    """
    from cosmos.core import i18n
    try:
        value = int(price or 0)
    except (TypeError, ValueError):
        value = 0
    if not value:
        return i18n.t("Price unknown")
    return f"{value:,} {str(currency or 'KRW').upper()}"


def signals_worth_showing(items: list[dict]) -> list[str]:
    """이 후보들에서 **누구 하나라도 아는** 신호만. ★순수 함수★

    ★아무도 모르는 신호는 칸을 차지하지 않는다★ 화면은 모르는 값을 *"모름"* 으로
    그리는데(빈칸은 "없다"로 읽히니까 옳다), 넷이 다 *"모름"* 인 줄은 아무것도
    말하지 않으면서 자리만 먹는다 — 그리고 그런 줄이 여섯이면 **정작 갈리는 신호가
    묻힌다**. 순서는 코어의 표를 따른다(화면이 자기 순서를 지어내지 않는다).
    """
    out = []
    for key in TRUST_SIGNALS:
        if any((i.get("signals") or {}).get(key) not in (None, "") for i in items
               if isinstance(i, dict)):
            out.append(key)
    return out


# ── 기억 — 의도와 후보를 브레인에 남긴다 ────────────────────────────────────

def migrate_products_once(brain, user_id: str, done_mark=None) -> None:
    """옛 후보(`kind="item"`)를 `product`로 한 번 옮긴다.

    ★**이름이 아니라 자리로 판정한다**★ — "무엇이 쇼핑 후보인가"를 상품명으로
    맞히려 들면 사용자가 진짜 소유한 물건까지 끌려온다. 후보는 **`considering`
    관계의 도착점**이라는 사실 하나로 정확히 갈린다.

    실패하면 표시를 남기지 않는다 — 다음에 다시 해 본다. 절반만 옮긴 채 "다 했다"고
    적히면 남은 절반은 영영 `item`에 남는다.
    ★표시를 **우리 폴더에** 둔다★(2026-08-19 · 마켓으로 나오면서) 예전에는 코어의
    표시 창고(`core.store`)를 썼는데, 그것은 코어의 살림이지 마켓 에이전트가 기댈
    자리가 아니다 — 남이 만든 에이전트는 그 문을 쓸 수 없다. 우리도 같은 규율을
    따른다(★에이전트 하나 = 파일 하나★).
    """
    if done_mark is None:
        return                             # 표시할 자리를 모르면 하지 않는다
    if done_mark.exists():
        return
    try:
        # 철회된 것까지 본다 — 지금 안 보이는 노드도 되살아나면 소유물로 보인다.
        entities, relations = brain.export_graph(user_id, limit=2000,
                                                 include_revoked=True)
        by_id = {e.id: e for e in entities}
        for relation in relations:
            if relation.rel != "considering":
                continue
            node = by_id.get(relation.dst)
            if node is not None and node.kind == "item":
                brain.update_entity(user_id, node.id, kind=PRODUCT_KIND)
    except Exception:
        return
    try:
        done_mark.parent.mkdir(parents=True, exist_ok=True)
        done_mark.write_text(now_ts(), encoding="utf-8")
    except OSError:
        pass                               # 못 적으면 다음에 다시 한다(멱등이다)


def remember_search(brain, user_id: str, query: str,
                    candidates: list[Candidate], *, now: str = "",
                    agent=None) -> str:
    """이번 검색을 **기억으로** 남긴다. 만든 `wish` 엔티티의 id를 돌려준다.

    ★에이전트 자체 저장소가 아니라 브레인에 두는 것이 요점이다★ — 그래야
    *"요즘 뭐 사려고 했지?"* 에 답하고, 다음 실행이 지난번을 안다.
    """
    stamp = now or now_ts()
    trust = Trust(confidence=1.0, provenance="user", source_channel=CHANNEL)
    # ★`provenance="user"`인 이유★ 무엇을 사려는지는 **사용자가 말한 것**이다.
    # 후보는 우리가 찾았지만 의도는 그 사람의 것이라, 자동 파이프라인이 덮으면 안 된다.
    #
    # 이미 보고 있던 의도가 있으면 **그 이름을 그대로 쓴다** — `upsert_entity`는
    # 이름으로 합치므로, 이름이 갈리면 같은 물건을 두 곳에 쌓게 된다.
    existing = _find_wish(brain, user_id, query)
    wish_id = brain.upsert_entity(user_id, Entity(
        name=existing.name if existing else _wish_name(query), kind="wish",
        attrs={**trust.to_attrs(), "query": query, "last_searched": stamp},
        valid_from=stamp))
    if not wish_id:
        return ""                    # 사용자가 지운 항목 — 되살리지 않는다(툼스톤)

    found = Trust(confidence=0.8, provenance="extracted", source_channel=CHANNEL)
    product_ids: list[str] = []
    for c in candidates[:PAGE_SIZE]:
        item_id = brain.upsert_entity(user_id, Entity(
            name=c.title[:120], kind=PRODUCT_KIND,
            attrs={**found.to_attrs(), "price": c.price, "currency": c.currency,
                   "seller": c.seller, "url": c.url, "seen_at": c.seen_at or stamp,
                   "affiliate": bool(c.affiliate), "signals": dict(c.signals or {})},
            valid_from=stamp))
        if item_id:
            product_ids.append(item_id)
            brain.upsert_relation(user_id, Relation(
                src=wish_id, dst=item_id, rel="considering",
                attrs={**found.to_attrs(), "price": c.price,
                       "seen_at": c.seen_at or stamp},
                valid_from=stamp))
    # ★누가 찾아 온 것인가★(R4) 산출물이 출처 에이전트를 가리킨다 — 그래야
    # *"이건 누가 찾아 온 거야?"* 에 답하고, 그 에이전트를 지울 때 함께 걷어낼 수 있다.
    # `agent`가 없으면 조용히 건너뛴다(코어를 직접 부르는 테스트·스크립트가 있다).
    if agent is not None:
        provenance.record(brain, user_id, agent, product_ids, now=stamp)

    # ★이 기억은 무엇에 **대한** 것인가★(R1) 의도와 후보를 **함께** 가리킨다 —
    # 그래야 *"이어폰"* 으로 검색했을 때 상품명만 적힌 기억까지 그래프로 닿는다.
    # `wish_id`는 호환을 위해 남긴다(화면·회상이 그 이름으로 읽는 자리가 있다).
    brain.remember(user_id, MemoryItem(
        text=_search_note(query, candidates), kind=ITEM_KIND, ts=stamp,
        meta={"query": query, "wish_id": wish_id, **trust.to_attrs(),
              **entity_links(wish_id, *product_ids)}))
    return wish_id


def remember_checkout(brain, user_id: str, query: str, title: str, origin: str,
                      *, now: str = "", agent=None) -> str:
    """★결제까지 갔다는 사실을 남긴다★ (Phase AS · AS-7 · 원칙 0 ①②)

    ★순간값이 아니라 **나중에도 참인 것**을 남긴다★ *"지금 29,900원"* 은 후보에
    `seen_at`과 함께 이미 있다. 여기 남기는 것은 *"2026-08-07에 이 물건의 결제까지
    갔다"* 이고, 그것은 반 년 뒤에도 참이다.

    ★그런데 "샀다"고는 적지 않는다★ 우리가 결제를 실행하지 않으므로 알 방법이 없고,
    추측해서 상태를 바꾸면 그것이 곧 오염이다(`compare_with_past`의 규칙 그대로).
    적는 것은 **갔다**까지이고, 샀는지는 다음번에 **묻는다**.

    `provenance="user"`인 이유: 사람이 버튼을 눌렀다. 자동 파이프라인이 덮으면 안 되고,
    지웠던 항목이라도 사람이 다시 고른 것이면 되살아나야 한다(툼스톤 통과 규칙).
    """
    stamp = now or now_ts()
    wish = _find_wish(brain, user_id, query)
    if wish is None:
        return ""
    trust = Trust(confidence=1.0, provenance="user", source_channel=CHANNEL)
    # ★attrs는 **병합된다**★(D29) — 다음 검색이 가격을 갱신해도 이 표시는 남는다.
    # 그래서 새 노드를 만들지 않고 같은 이름으로 upsert한다.
    product_id = brain.upsert_entity(user_id, Entity(
        name=str(title or "")[:120], kind=PRODUCT_KIND,
        attrs={**trust.to_attrs(), "checkout_at": stamp, "checkout_origin": origin},
        valid_from=stamp))
    if product_id:
        brain.upsert_relation(user_id, Relation(
            src=wish.id, dst=product_id, rel="considering",
            attrs={**trust.to_attrs(), "checkout_at": stamp}, valid_from=stamp))
        if agent is not None:
            provenance.record(brain, user_id, agent, [product_id], now=stamp)
    # ★회상으로도 닿아야 한다★(원칙 0 ④) 의도와 상품명이 함께 들어가야 어느 낱말로
    # 물어도 걸린다 — *"이어폰 결제하려던 거"* 와 *"소니 그거"* 는 다른 낱말이다.
    brain.remember(user_id, MemoryItem(
        text=_checkout_note(query, title, origin), kind=ITEM_KIND, ts=stamp,
        meta={"query": query, "wish_id": wish.id, "checkout": True, "origin": origin,
              **trust.to_attrs(), **entity_links(wish.id, product_id)}))
    return product_id


def _checkout_note(query: str, title: str, origin: str) -> str:
    """회상에 걸리는 문장. ★값 없는 부분은 영어다★(CLAUDE.md 0-b) — 상품명·검색어는
    사용자의 낱말 그대로여야 검색이 닿는다."""
    where = f" on {origin}" if origin else ""
    return f"Went to checkout for {title}{where} while looking for {query}"


def recall_search(brain, user_id: str, query: str) -> dict:
    """지난번에 이 물건을 어디까지 봤나. 없으면 빈 dict.

    **후보의 그때 가격까지** 돌려주는 것이 요점이다 — 그래야 "얼마나 움직였는지"를
    말할 수 있다. 지금 가격만 알면 "12,000원 내렸어요"가 나오지 않는다.
    """
    wish = _find_wish(brain, user_id, query)
    if wish is None:
        return {}
    seen = []
    for entity, relation in brain.neighbors(user_id, wish.id, rel="considering"):
        attrs = entity.attrs or {}
        seen.append({
            "title": entity.name,
            "price": int((relation.attrs or {}).get("price") or attrs.get("price") or 0),
            "seller": attrs.get("seller", ""),
            "url": attrs.get("url", ""),
            "seen_at": (relation.attrs or {}).get("seen_at") or attrs.get("seen_at", ""),
            # ★결제까지 갔던 것은 다음번에 **물어야 할 것**이다★(원칙 0 ③)
            # 이 칸이 없으면 `remember_checkout`은 쌓기만 하고 쓰는 문이 없어진다 —
            # 이 저장소가 여섯 번 데인 바로 그 실패다.
            "checkout_at": attrs.get("checkout_at", ""),
        })
    return {"query": (wish.attrs or {}).get("query") or query,
            "wish_id": wish.id,
            "last_searched": (wish.attrs or {}).get("last_searched", ""),
            "candidates": seen}


def _wish_name(query: str) -> str:
    """의도의 **표시 이름** — 검색어에서 부탁하는 말만 걷어낸다.

    사람이 읽는 이름이므로 띄어쓰기를 그대로 둔다. 같은 의도인지 가르는 것은
    `_same_intent`의 몫이다(아래).
    """
    import re
    text = str(query or "").strip()
    text = re.sub(r"(추천|찾아줘|찾아봐|알아봐|사려고|살까|해줘|검색)", " ", text)
    text = re.sub(r"[^0-9A-Za-z가-힣\s]+", " ", text)
    return " ".join(text.split())[:120] or str(query or "").strip()[:120]


def _same_intent(a: str, b: str) -> bool:
    """★한국어는 띄어쓰기가 유동적이다★ *"무선 이어폰"*과 *"무선이어폰"*은 같은
    물건인데, 이름이 다르면 **따로 쌓여서 "지난번"을 영영 못 찾는다**.

    띄어쓰기를 지운 채로 비교하되, **표시 이름은 처음 것을 그대로 쓴다** —
    비교 편의를 위해 화면의 낱말을 뭉개면 `무선이어폰`처럼 어색해진다.
    (영어에도 안전하다: 공백을 지운 문자열끼리만 비교하므로 `wireless earbuds`와
    `wirelessearbuds`가 같아지는데, 그 둘은 실제로 같은 물건이다.)
    """
    return a.replace(" ", "").lower() == b.replace(" ", "").lower()


def _find_wish(brain, user_id: str, query: str):
    """이미 보고 있던 같은 의도가 있으면 그것. 없으면 None."""
    name = _wish_name(query)
    for entity in brain.find_entities(user_id, kind="wish"):
        if _same_intent(entity.name, name):
            return entity
    return None


def _search_note(query: str, candidates: list[Candidate]) -> str:
    """회상에 걸리는 문장. 후보 이름을 담는 이유는 나중에 상품명으로도 찾기 위해서다."""
    names = " · ".join(c.title for c in candidates[:PAGE_SIZE])
    return f"{query} 을(를) 찾아봤다: {names}" if names else f"{query} 을(를) 찾아봤다"


# ── 두 번째 실행 — ★이 페이즈의 심장★(Sean 요구 6) ─────────────────────────

# 지난 검색이 이보다 오래됐으면 "지난번"이라고 부르지 않는다. 반 년 전에 한 번
# 검색한 것을 들이밀면 도움이 아니라 참견이다.
STALE_AFTER_DAYS = 60


def compare_with_past(past: dict, fresh: list[Candidate], *, now: str = "") -> dict:
    """지난번과 이번을 나란히 놓는다 — **무엇을 말할지**까지 정한다.

    *"지난주에 망설이던 그 이어폰, 12,000원 내렸어요"* 가 나오는 자리다.
    반환은 화면과 말이 **같은 것을 읽도록** 한 벌로 준다:

    - `first_time`  — 처음 보는 물건인가
    - `changes`     — 값이 움직인 후보들(내림/오름)
    - `gone`        — 지난번엔 있었는데 이번엔 없는 것(품절·단종일 수 있다)
    - `new`         — 이번에 새로 보이는 것
    - `stale`       — 지난 검색이 너무 오래됐다(그때는 "지난번"을 들이밀지 않는다)
    - `checked_out` — 지난번에 **결제까지 갔던** 후보들(AS-7)

    ★"샀는지"는 여기서 **판정하지 않는다**★ 결제를 우리가 하지 않는 한 알 방법이
    없고, 추측해서 상태를 바꾸면 그것이 곧 오염이다. 묻는 것은 부르는 쪽의 몫이다.
    `checked_out`도 **사실만** 담는다(*"갔다"*) — *"샀다"* 로 옮기는 순간 위 규칙이
    무너진다. 그 사실로 무엇을 물을지는 화면과 말이 정한다.
    """
    if not past or not past.get("candidates"):
        return {"first_time": True, "changes": [], "gone": [], "new": [],
                "stale": False, "checked_out": []}

    before = {_normalise_title(c["title"]): c for c in past["candidates"]}
    after = {c.key(): c for c in fresh}

    changes = []
    for key, old in before.items():
        new = after.get(key)
        if new is None:
            continue
        move = price_change(int(old.get("price") or 0), int(new.price or 0))
        if move["changed"]:
            changes.append({"title": new.title, "before": old.get("price"),
                            "after": new.price, **move})
    # 큰 변화를 먼저 — 화면과 말 모두 **가장 중요한 것부터** 나와야 한다
    changes.sort(key=lambda c: -abs(c["delta"]))

    return {
        "first_time": False,
        "changes": changes,
        "gone": [old["title"] for key, old in before.items() if key not in after],
        "new": [c.title for key, c in after.items() if key not in before],
        "stale": _is_stale(past.get("last_searched", ""), now),
        "last_searched": past.get("last_searched", ""),
        # ★지금도 보이는 것만 묻는다★ 사라진 후보를 두고 *"샀나요?"* 라고 물으면
        # 사용자는 확인할 방법이 없다(품절·단종은 `gone`이 이미 말한다).
        "checked_out": [{"title": after[key].title, "at": old.get("checkout_at", "")}
                        for key, old in before.items()
                        if old.get("checkout_at") and key in after],
    }


def _is_stale(last: str, now: str = "") -> bool:
    """지난 검색이 너무 오래됐나 — 반 년 전 것을 들이밀면 참견이다."""
    from datetime import datetime
    if not last:
        return False
    try:
        then = datetime.fromisoformat(last)
        current = datetime.fromisoformat(now) if now else datetime.now()
    except ValueError:
        return False
    return (current - then).days > STALE_AFTER_DAYS
