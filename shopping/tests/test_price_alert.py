"""★값이 내리면 **먼저** 말한다★ (Sean 요구 2026-08-18)

> *"백그라운드에서 아직 **구매 여부를 확인**이 되었다면 그리고 아직 **구매 욕구가
>  있다**는 것을 확인한 경우, **가격 인하나 특별 이벤트**가 생기는 경우 **바로
>  알림**을 해서 구매를 도울 수 있도록 하는 것이 목표에 있어야 함."*

이 파일이 지키는 것 넷:

  ① ★산 사람에게는 말하지 않는다★ 사고 나서 *"더 싸졌어요"* 는 도움이 아니라 상처다
  ② ★알림은 화면보다 문턱이 높다★ 화면은 지나가다 보는 것이고 알림은 멈추게 하는 것이다
  ③ ★해소되면 스스로 내려간다★ 안 내려가는 알림은 두 번째부터 무시당한다
  ④ **답을 적는다** — 안 적으면 열 번을 물어도 매번 처음이다
"""
from __future__ import annotations

import json

import pytest

import shopping_core as shopping
from shopping_core import (
    ALERT_MIN_DELTA, ALERT_MIN_RATIO, Candidate, due_for_recheck,
    remember_outcome, remember_search, still_wanted, watchlist, worth_interrupting,
)
from shopping_scout import ShoppingPlugin
from cosmos.runtime.memory_lite.provider import LiteMemoryProvider

USER = "u1"


@pytest.fixture()
def brain(tmp_path):
    return LiteMemoryProvider(tmp_path / "brain")


def _c(title, price, **kw):
    return Candidate(title=title, price=price, seen_at="2026-08-18T10:00:00", **kw)


# ── ① 산 사람에게는 말하지 않는다 ───────────────────────────────────────────

def test_something_already_bought_is_not_watched():
    """★사고 나서 "더 싸졌어요"는 도움이 아니라 상처다★"""
    assert still_wanted({"seen_at": "2026-08-18T10:00:00"})
    assert not still_wanted({"seen_at": "2026-08-18T10:00:00",
                             "bought_at": "2026-08-18T11:00:00"})


def test_something_given_up_on_is_not_watched():
    """사람이 접은 것을 계속 들이밀면 그것은 참견이다."""
    assert not still_wanted({"seen_at": "2026-08-18T10:00:00",
                             "dropped_at": "2026-08-18T11:00:00"})


def test_going_to_checkout_is_not_the_same_as_buying():
    """★우리가 결제를 실행하지 않으므로 "샀다"는 알 수 없다★

    `checkout_at`만으로 지켜보기를 끄면, **정말 아직 안 산 사람의 알림이 사라진다**.
    끄는 것은 사람이 *"샀어"* 라고 말한 것뿐이다.
    """
    assert still_wanted({"seen_at": "2026-08-18T10:00:00",
                         "checkout_at": "2026-08-18T10:30:00"})


def test_a_half_year_old_wish_is_left_alone():
    assert not still_wanted({"seen_at": "2025-01-01T10:00:00"},
                            now="2026-08-18T10:00:00")


# ── ② 알림은 화면보다 문턱이 높다 ────────────────────────────────────────────

def test_the_bar_for_interrupting_is_higher_than_the_bar_for_the_screen():
    """★화면은 지나가다 보는 것이고 알림은 하던 일을 멈추게 하는 것이다★"""
    assert ALERT_MIN_RATIO > shopping.PRICE_CHANGE_MIN_RATIO, \
        "알림 문턱이 화면 문턱과 같거나 낮습니다 — 그러면 잔소리가 됩니다"


def test_a_real_drop_is_worth_saying():
    got = worth_interrupting(1_000_000, 880_000)
    assert got["tell"] and got["reason"] == "cheaper" and got["delta"] == -120_000


def test_a_small_wobble_is_not():
    """100원 차이를 알리면 그것은 소음이다."""
    assert not worth_interrupting(1_000_000, 985_000)["tell"]      # 1.5%
    # 비율은 넘지만 금액이 작은 것도 아니다 — 싼 물건이 하루에 몇 번씩 울린다
    small = worth_interrupting(10_000, 10_000 - ALERT_MIN_DELTA + 1)
    assert not small["tell"] and small["reason"] == "too_small"


def test_a_price_going_up_is_never_an_interruption():
    """★"12,000원 올랐어요"로 살 수 있는 사람은 없다★ 그 사실은 화면이 말한다."""
    got = worth_interrupting(880_000, 1_000_000)
    assert not got["tell"] and got["reason"] == "not_cheaper"


def test_the_same_thing_is_not_raised_two_days_running():
    """오르내리는 물건은 문턱만으로는 하루에 몇 번씩 울린다."""
    got = worth_interrupting(1_000_000, 880_000,
                             last_alert="2026-08-18T09:00:00",
                             now="2026-08-18T21:00:00")
    assert not got["tell"] and got["reason"] == "told_recently"
    # 조용한 기간이 지나면 다시 말할 수 있다
    assert worth_interrupting(1_000_000, 880_000,
                              last_alert="2026-08-01T09:00:00",
                              now="2026-08-18T21:00:00")["tell"]


def test_never_checked_means_check_now():
    """★빈 값을 "방금 봤다"로 읽으면 영영 안 본다★"""
    assert due_for_recheck("")
    assert due_for_recheck("이건 시각이 아니다")
    assert not due_for_recheck("2026-08-18T09:00:00", now="2026-08-18T10:00:00")
    assert due_for_recheck("2026-08-17T09:00:00", now="2026-08-18T10:00:00")


# ── ③④ 브레인까지 이어지는가 ────────────────────────────────────────────────

def test_the_watchlist_only_holds_what_is_still_open(brain):
    """★되읽는 문★ 이것이 없으면 `remember_outcome`은 쌓기만 하고 쓰는 곳이 없다."""
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    remember_search(brain, USER, "선풍기", [_c("다이슨 쿨", 500_000)])
    assert {r["query"] for r in watchlist(brain, USER)} == {"무선 이어폰", "선풍기"}

    remember_outcome(brain, USER, "무선 이어폰", "소니 WF-1000XM5", "bought")
    assert {r["query"] for r in watchlist(brain, USER)} == {"선풍기"}


def test_saying_you_have_not_bought_it_after_all_puts_it_back(brain):
    """★못 되돌리는 기록은 사람이 말하기를 망설이게 만든다★"""
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    remember_outcome(brain, USER, "무선 이어폰", "소니 WF-1000XM5", "bought")
    assert not watchlist(brain, USER)
    remember_outcome(brain, USER, "무선 이어폰", "소니 WF-1000XM5", "")
    assert [r["query"] for r in watchlist(brain, USER)] == ["무선 이어폰"]


def test_the_decision_is_the_users_and_cannot_be_overwritten(brain):
    """★사용자 발화·결정이 언제나 이긴다★ 어떤 자동 파이프라인도 못 덮는다."""
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    remember_outcome(brain, USER, "무선 이어폰", "소니 WF-1000XM5", "bought")
    node = next(e for e in brain.find_entities(USER, kind="product")
                if e.name == "소니 WF-1000XM5")
    assert node.attrs.get("provenance") == "user"
    assert node.attrs.get("bought_at")


def test_one_wish_is_watched_by_one_candidate_only(brain):
    """넷을 다 지켜보면 한 물건으로 알림이 넷 울린다 — 가장 싼 것 하나다."""
    remember_search(brain, USER, "무선 이어폰",
                    [_c("비싼 것", 400_000), _c("싼 것", 200_000)])
    rows = watchlist(brain, USER)
    assert len(rows) == 1 and rows[0]["watching"]["title"] == "싼 것"


# ── ⑤ 훅이 **실제로** 도는가 (선언만 보면 배선이 끊겨도 초록이다) ────────────

class _Ctx:
    def __init__(self, tmp_path, brain, *, search="결과", extract="[]"):
        self._dir, self.brain, self.user_id = tmp_path, brain, USER
        self._search, self._extract = search, extract
        self.notices: dict[str, dict] = {}
        self.cleared: list[str] = []
        self.logs: list[str] = []

    def data_dir(self, component):
        path = self._dir / "agentdata" / component
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_log(self, message, speaker=None, level="info"):
        self.logs.append(message)

    def run_tool(self, name, args):
        return self._search

    def think(self, prompt, *, system=None, fast=False):
        return self._extract

    def notice(self, key, title, *, level="info", detail="", action=None):
        self.notices[key] = {"title": title, "level": level, "detail": detail,
                             "action": action}
        return True

    def clear_notice(self, key):
        self.cleared.append(key)
        return self.notices.pop(key, None) is not None


_CHEAPER = json.dumps([{"title": "소니 WF-1000XM5", "price": 240_000,
                        "seller": "쿠팡", "url": "https://example.com/a",
                        "signals": {"rating": 4.6}}], ensure_ascii=False)


def test_the_hook_is_declared_so_the_user_can_turn_it_off():
    """★끄면 정말로 안 불려야 한다★ 선언이 없으면 코스모스가 부를 수도, 끌 수도 없다."""
    from cosmos.contracts import hooks
    assert ShoppingPlugin.raises_notices is True
    assert hasattr(ShoppingPlugin, hooks.HOOKS["notice"]["method"])


def test_a_price_drop_actually_raises_a_notice(brain, tmp_path):
    """★배선까지 잰다★ 판정 함수만 검사하면 `advise()`가 비어 있어도 초록이다."""
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    agent = ShoppingPlugin()
    ctx = _Ctx(tmp_path, brain, extract=_CHEAPER)
    agent.advise(ctx)
    assert ctx.notices, "값이 49,000원 내렸는데 아무 말도 안 했습니다"
    (key, said), = ctx.notices.items()
    assert key.startswith("price:")
    assert "cheaper" in said["title"].lower()
    assert said["level"] == "warn", "말로도 나가야 한다(info는 조용하다)"
    assert said["action"]["tool"] == "shopping", "누를 것이 없으면 알림이 반쪽이다"


def test_nothing_is_said_about_something_already_bought(brain, tmp_path):
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    remember_outcome(brain, USER, "무선 이어폰", "소니 WF-1000XM5", "bought")
    ctx = _Ctx(tmp_path, brain, extract=_CHEAPER)
    ShoppingPlugin().advise(ctx)
    assert not ctx.notices, "★산 사람에게 더 싸졌다고 말했습니다★"


def test_the_notice_comes_down_by_itself_once_it_is_bought(brain, tmp_path):
    """★내리는 것이 절반이다★ 안 내려가는 알림은 두 번째부터 무시당한다."""
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    agent = ShoppingPlugin()
    ctx = _Ctx(tmp_path, brain, extract=_CHEAPER)
    agent.advise(ctx)
    assert ctx.notices

    remember_outcome(brain, USER, "무선 이어폰", "소니 WF-1000XM5", "bought")
    agent.advise(ctx)
    assert not ctx.notices, "샀는데 알림이 그대로 떠 있습니다"
    assert ctx.cleared, "내리는 문을 부르지 않았습니다"


def test_the_new_price_is_written_down_after_telling(brain, tmp_path):
    """★새 값을 안 남기면 **같은 인하를 매번 다시** 알린다★

    ⚠️ 이 그물은 처음에 *"두 번 부르면 두 번째는 조용한가"* 로 썼는데 **공짜로
    통과했다** — 재점검 주기(`due_for_recheck`)가 두 번째 호출을 아예 막아서, 값을
    안 남겨도 초록이었다(뮤테이션이 잡았다). 막아 주는 것이 하나 더 있으면 정작
    검사하려던 것은 검사되지 않는다.

    그래서 **기억된 값 자체**를 본다. 이것이 다시 안 알리는 진짜 이유다.
    """
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    agent = ShoppingPlugin()
    ctx = _Ctx(tmp_path, brain, extract=_CHEAPER)
    agent.advise(ctx)
    assert ctx.notices, "★측정 무효★ 알림 자체가 안 떴습니다"
    assert watchlist(brain, USER)[0]["watching"]["price"] == 240_000, \
        "새 값을 기억에 안 남겼습니다 — 조용한 기간이 지나면 같은 소식이 또 나갑니다"


def test_it_does_not_search_again_on_every_single_turn(brain, tmp_path):
    """★`advise()`는 말이 오갈 때마다 불린다★ 매번 검색하면 대화 한 번에 웹 검색이
    지켜보는 수만큼 나간다. 점검한 시각을 남기고, 때가 되기 전에는 안 본다."""
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    agent = ShoppingPlugin()

    searches = []

    class _Counting(_Ctx):
        def run_tool(self, name, args):
            searches.append(name)
            return self._search

    ctx = _Counting(tmp_path, brain, extract=_CHEAPER)
    agent.advise(ctx)
    first = len(searches)
    assert first, "★측정 무효★ 한 번도 안 찾아봤습니다"
    agent.advise(ctx)
    assert len(searches) == first, "말이 오갈 때마다 다시 검색하고 있습니다"


def test_a_background_check_keeps_everything_else_the_wish_knows(brain):
    """★적는 것만 보고 **적고 나서 되읽는 것**을 안 봤다★ (2026-08-19 실측)

    `remember_check`가 `update_entity`에 적을 것만 넘기고 있었다. 그 문은 attrs를
    **병합하지 않고 갈아 끼운다** — 그래서 배경 점검이 한 번 돌면 그 의도가 아는
    나머지가 전부 사라졌고, 남은 것은 `last_checked` 하나였다.

    ★사라진 여덟이 전부 이 기능이 서 있는 바닥이었다★
      · `price`·`currency` — *"그때 얼마였나"*. 없으면 *"내렸어요"* 를 못 말한다
      · `last_alert`       — 조용히 기다리는 사흘. 없으면 **같은 물건을 매번 알린다**
      · `provenance=user`  — 없으면 자동 파이프라인이 이 의도를 덮는다(불변 규칙)

    ⚠️ 이 검사는 **한 칸씩** 이름을 대지 않는다. 그러면 나중에 칸이 하나 늘 때
    그것만 조용히 사라져도 초록이다 — *"점검 전에 알던 것을 점검 뒤에도 아는가"*
    를 통째로 묻는다.
    """
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    row = watchlist(brain, USER)[0]
    before = dict(brain.get_entity(USER, row["wish_id"]).attrs or {})
    assert before.get("provenance") == "user", "★측정 무효★ 잴 것이 애초에 없습니다"

    shopping.remember_check(brain, USER, row["wish_id"])

    after = dict(brain.get_entity(USER, row["wish_id"]).attrs or {})
    assert after.get("last_checked"), "점검한 시각을 안 적었습니다"
    lost = sorted(k for k in before if k not in after)
    assert not lost, f"점검이 이 의도가 알던 것을 지웠습니다: {lost}"
    assert all(after[k] == v for k, v in before.items()), "값이 바뀌었습니다"


def test_a_pinned_wish_is_still_checked_off(brain):
    """★고정은 **사실**을 지키는 것이지 살림을 얼리는 것이 아니다★

    `upsert_entity`는 `pinned`이 걸린 노드의 자동 갱신을 통째로 무시한다. 거기에
    점검 시각을 맡기면 고정한 의도만 **영영 안 적히고**, `due_for_recheck`가 늘
    참이 되어 ★대화마다 웹 검색이 나간다★.
    """
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289_000)])
    row = watchlist(brain, USER)[0]
    node = brain.get_entity(USER, row["wish_id"])
    brain.update_entity(USER, row["wish_id"],
                        attrs={**(node.attrs or {}), "pinned": True})

    shopping.remember_check(brain, USER, row["wish_id"])

    after = dict(brain.get_entity(USER, row["wish_id"]).attrs or {})
    assert after.get("last_checked"), "고정한 의도는 점검 시각이 안 적힙니다"
    assert after.get("pinned") is True, "고정을 지웠습니다"
    assert not due_for_recheck(after["last_checked"]), \
        "적었는데도 또 볼 때가 됐다고 합니다"


def test_saying_i_bought_it_through_the_tool_is_written_down(brain, tmp_path):
    """*"샀나요?"* 의 답이 **어딘가에 남아야** 다음번에 안 묻는다."""
    agent = ShoppingPlugin()
    ctx = _Ctx(tmp_path, brain, extract=json.dumps(
        [{"title": "소니 WF-1000XM5", "price": 289_000,
          "url": "https://example.com/a"}], ensure_ascii=False))
    agent.run(ctx, query="무선 이어폰")
    said = agent.run(ctx, action="bought", index=1)
    assert "yours" in said.lower() or "stop watching" in said.lower()
    assert not watchlist(brain, USER), "★답을 받고도 계속 지켜보고 있습니다★"
