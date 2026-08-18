"""쇼핑 코어(Phase S §S1~S3) — **기억하는 쇼핑 도우미**.

쇼핑 검색은 세상에 많다. 우리가 만드는 것은 검색이 아니라 **기억**이다.
이 파일이 지키는 것 다섯:

  ① ★**의도가 브레인에 저장된다**★ — 에이전트 자체 저장소에 두면 브레인이 모르고,
     그러면 "요즘 뭐 사려고 했지?"에 답할 수 없다
  ② ★**수수료가 순위를 바꾸지 않는다**★ — 바꾸는 순간 이 기능의 목적이 뒤집힌다
  ③ **모르는 신호는 "모름"이다** — 빈칸은 "없다"로 읽히고, 그것이 곧 거짓말이다
  ④ **가격에는 잰 시각이 붙는다** — 낡은 값을 지금 값처럼 보이면 신뢰가 한 번에 깨진다
  ⑤ **같은 상품은 판매처가 달라도 하나로 묶인다**
"""
from __future__ import annotations

import pytest

import shopping_core as shopping
from shopping_core import (
    Candidate, price_change, rank, recall_search, remember_search, visible_signals,
)
from cosmos.runtime.memory_lite.provider import LiteMemoryProvider

USER = "u1"


@pytest.fixture()
def brain(tmp_path):
    return LiteMemoryProvider(tmp_path / "brain")


def _c(title, price=0, *, rating=None, affiliate=False, seller="", **signals):
    sig = {k: v for k, v in signals.items() if v is not None}
    if rating is not None:
        sig["rating"] = rating
    return Candidate(title=title, price=price, seller=seller, affiliate=affiliate,
                     signals=sig, seen_at="2026-08-03T10:00:00")


# ── ① 의도가 브레인에 저장된다 ──────────────────────────────────────────────

def test_what_i_am_shopping_for_is_in_the_brain(brain):
    """★핵심 결정★ 에이전트 안에 두면 브레인이 모르고, 그러면 다른 어떤 경로로도
    "요즘 뭐 사려고 했지?"에 답할 수 없다."""
    wish_id = remember_search(brain, USER, "무선 이어폰",
                              [_c("소니 WF-1000XM5", 289000), _c("젠하이저 모멘텀", 254000)])
    assert wish_id

    wishes = brain.find_entities(USER, kind="wish")
    assert [w.name for w in wishes] == ["무선 이어폰"]
    linked = {e.name for e, _ in brain.neighbors(USER, wish_id, rel="considering")}
    assert linked == {"소니 WF-1000XM5", "젠하이저 모멘텀"}


def test_the_intent_is_the_users_own_word(brain):
    """★사용자 발화가 언제나 이긴다★ 무엇을 사려는지는 그 사람이 말한 것이다 —
    자동 파이프라인이 덮으면 안 된다."""
    remember_search(brain, USER, "무선 이어폰", [_c("A", 1000)])
    wish = brain.find_entities(USER, kind="wish")[0]
    assert wish.attrs.get("provenance") == "user"


def test_the_same_intent_in_different_words_lands_in_one_place(brain):
    """*"무선 이어폰"*과 *"무선이어폰 추천해줘"*는 **같은 의도**다 — 따로 쌓이면
    "지난번"을 영영 못 찾는다."""
    remember_search(brain, USER, "무선 이어폰", [_c("A", 1000)])
    remember_search(brain, USER, "무선이어폰 추천해줘", [_c("B", 2000)])
    assert len(brain.find_entities(USER, kind="wish")) == 1


def test_what_i_wanted_is_not_what_i_own(brain):
    """★`item`에 섞이면 "내가 뭘 갖고 있지?"에 사지도 않은 게 나온다★

    ⚠️ **이 그물에 구멍이 있었다**(K2-0 실측): 원래는 **의도 이름**(*"무선 이어폰"*)이
    소유물에 없는지만 봤고, 정작 소유물로 들어가던 것은 **후보 상품**
    (*"소니 WF-1000XM5"*)이었다. 검사가 지키던 것보다 **한 칸 옆**이 새고 있었다 —
    13차 교훈 ①(*"목록을 만든 것을 의심하라"*)이 그물 자신에게도 적용된다.
    """
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289000)])
    owned = {e.name for e in brain.find_entities(USER, kind="item")}
    wished = {e.name for e in brain.find_entities(USER, kind="wish")}
    assert "무선 이어폰" not in owned, "사려는 것이 소유물로 들어갔다"
    assert wished == {"무선 이어폰"}
    # ★한 칸 옆까지 본다★ 사지도 않은 상품이 소유물이면 안 된다.
    assert owned == set(), f"검토만 한 상품이 소유물로 들어갔다: {owned}"
    assert {e.name for e in brain.find_entities(USER, kind="product")} \
        == {"소니 WF-1000XM5"}


def test_a_candidate_stored_as_a_belonging_long_ago_is_moved(brain, tmp_path):
    """★마이그레이션 — 이미 쓰던 사람의 그래프에는 옛 후보가 `item`으로 남아 있다★

    불변 규칙(*"마이그레이션 없이 스키마 변경 금지"*)이 이 자리를 가리킨다. 그냥
    갈아타면 그 사람의 *"내가 뭘 갖고 있지?"* 는 **영영** 오염된 채로 남는다.
    """
    from cosmos.contracts.memory import Entity, Relation
    wish_id = brain.upsert_entity(USER, Entity(name="이어폰", kind="wish"))
    old_id = brain.upsert_entity(USER, Entity(name="옛 후보", kind="item"))
    real_id = brain.upsert_entity(USER, Entity(name="내 노트북", kind="item"))
    brain.upsert_relation(USER, Relation(src=wish_id, dst=old_id, rel="considering"))
    # ★소유물에도 **관계를 매단다**★ 관계 없는 노드로만 재면 "`considering`만
    # 고른다"를 지워도 그물이 안 운다 — 뮤테이션이 실제로 그 구멍으로 빠져나갔다
    # (10차 함정 15: 테스트 데이터가 약하면 방어하는 경로를 아예 안 탄다).
    project_id = brain.upsert_entity(USER, Entity(name="집필", kind="project"))
    brain.upsert_relation(USER, Relation(src=project_id, dst=real_id, rel="uses"))

    shopping.migrate_products_once(brain, USER, tmp_path / 'mark')

    kinds = {e.name: e.kind for e in brain.find_entities(USER)}
    assert kinds["옛 후보"] == "product", "옛 후보가 소유물에 그대로 남았다"
    # ★진짜 소유물은 건드리지 않는다★ — 이름으로 맞히려 들면 여기가 무너진다
    assert kinds["내 노트북"] == "item", "사용자가 실제로 가진 것을 옮겨 버렸다"
    assert real_id and old_id


def test_moving_old_candidates_happens_only_once(brain, monkeypatch, tmp_path):
    """★멱등★ 매 검색마다 그래프 전체를 훑으면 검색이 느려진다."""
    calls = []
    real = type(brain).export_graph
    monkeypatch.setattr(type(brain), "export_graph",
                        lambda self, *a, **k: (calls.append(1), real(self, *a, **k))[1])
    shopping.migrate_products_once(brain, USER, tmp_path / 'mark')
    shopping.migrate_products_once(brain, USER, tmp_path / 'mark')
    assert len(calls) == 1, f"마이그레이션이 매번 돌았다({len(calls)}회)"


def test_a_search_can_be_recalled_with_the_prices_of_that_time(brain):
    """★그때 가격을 안 남기면 "12,000원 내렸어요"가 나오지 않는다★"""
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289000)])
    past = recall_search(brain, USER, "무선 이어폰")
    assert past["candidates"][0]["price"] == 289000
    assert past["candidates"][0]["seen_at"], "언제 잰 값인지 안 남았다"


def test_recalling_something_never_searched_is_empty_not_wrong(brain):
    assert recall_search(brain, USER, "냉장고") == {}


def test_a_wish_the_user_deleted_does_not_come_back(brain, monkeypatch):
    """툼스톤 — 지운 것을 자동 파이프라인이 되살리면 그 규칙은 없는 것과 같다."""
    monkeypatch.setattr(type(brain), "upsert_entity",
                        lambda self, uid, ent: "" if ent.kind == "wish" else "x")
    assert remember_search(brain, USER, "무선 이어폰", [_c("A", 1)]) == ""


# ── ② 수수료가 순위를 바꾸지 않는다 ─────────────────────────────────────────

def test_an_affiliate_link_never_climbs_the_list():
    """★이 규칙이 깨지면 기능의 목적이 뒤집힌다★ "믿고 안전한 곳"이라며 수수료를
    받는 곳을 올리는 것은 광고이지 도움이 아니다."""
    cheap_plain = _c("싼 것", 10000, rating=4.5)
    pricey_paid = _c("비싼 제휴", 30000, rating=4.5, affiliate=True)
    assert rank([pricey_paid, cheap_plain])[0].title == "싼 것"

    # 평점이 같고 가격도 같으면? — 그래도 수수료가 이유가 되어서는 안 된다
    same_paid = _c("같은값 제휴", 10000, rating=4.5, affiliate=True)
    same_plain = _c("같은값 일반", 10000, rating=4.5)
    order = [c.title for c in rank([same_paid, same_plain])]
    assert order == sorted(order), "정렬이 수수료 여부에 흔들렸다"


def test_a_better_rated_item_comes_first():
    order = [c.title for c in rank([_c("낮음", 1000, rating=3.0),
                                    _c("높음", 2000, rating=4.8)])]
    assert order[0] == "높음"


def test_an_item_without_a_price_does_not_lead():
    """비교할 수 없는 것을 앞에 두면 비교가 안 된다."""
    order = [c.title for c in rank([_c("모름", 0, rating=4.0),
                                    _c("아는 값", 5000, rating=4.0)])]
    assert order[0] == "아는 값"


def test_one_screen_stays_short_enough_to_decide_from():
    """★스크롤해야 비교가 되면 "한눈에 결정"이 깨진다★ 한 **화면**은 짧아야 한다."""
    many = [_c(f"후보{i}", 1000 + i, rating=4.0) for i in range(20)]
    shown, _, _ = shopping.page_of(rank(many))
    assert len(shown) == shopping.PAGE_SIZE
    assert 2 <= shopping.PAGE_SIZE <= 6, "한 화면에서 비교할 수 있는 수를 넘었다"


def test_the_ones_that_did_not_fit_are_kept_for_the_next_page():
    """★넷만 남기고 버리면 "다음 보기"라고 말할 것이 **없다**★ (Sean 요구 2026-08-18)

    예전에는 `rank`가 넷만 돌려주고 나머지를 버렸다. 그래서 마음에 드는 것이 없으면
    사용자가 **같은 검색을 다시** 해야 했다 — 그리고 순위가 흔들려 아까 본 것이 또
    나왔다. 한 화면이 짧은 것과 목록이 짧은 것은 다른 이야기다.
    """
    many = [_c(f"후보{i}", 1000 + i, rating=4.0) for i in range(20)]
    kept = rank(many)
    assert len(kept) == shopping.MAX_KEPT
    assert shopping.MAX_KEPT > shopping.PAGE_SIZE, "넘길 다음 쪽이 없다"


def test_the_last_page_does_not_wrap_around_to_the_first():
    """★끝은 끝이라고 말한다★ 되감으면 사용자는 그것을 **새 목록**으로 읽는다."""
    items = list(range(6))                      # 두 쪽(4 + 2)
    _, last_page, pages = shopping.page_of(items, 1)
    assert (last_page, pages) == (1, 2)
    # 마지막에서 한 번 더 넘겨도 제자리다 — 부르는 쪽은 이 "안 움직임"으로 끝을 안다
    _, still, _ = shopping.page_of(items, last_page + 1)
    assert still == last_page


def test_a_signal_nobody_knows_does_not_take_a_column():
    """★넷이 다 "모름"인 줄은 자리만 먹고 **갈리는 신호를 묻는다**★"""
    rows = [{"signals": {"rating": 4.5, "escrow": None}},
            {"signals": {"rating": 4.1}}]
    keys = shopping.signals_worth_showing(rows)
    assert "rating" in keys
    assert "escrow" not in keys and "seller_age" not in keys


# ── ③ 모르는 신호는 "모름"이다 ──────────────────────────────────────────────

def test_unknown_signals_are_shown_as_unknown_not_hidden():
    """★빈칸은 "없다"로 읽힌다★ 그리고 그것이 거짓말이 된다."""
    rows = visible_signals(_c("A", 1000, rating=4.2))
    by_key = {r["key"]: r for r in rows}
    assert set(by_key) == set(shopping.TRUST_SIGNALS), "신호를 빠뜨리고 그린다"
    assert by_key["rating"]["known"] is True and by_key["rating"]["value"] == 4.2
    assert by_key["escrow"]["known"] is False, "모르는 것을 아는 척한다"


def test_signals_are_never_collapsed_into_one_score():
    """*"이 판매처는 87점"* 은 그럴듯하지만 **근거가 없으면 거짓말**이다."""
    assert not hasattr(shopping, "trust_score"), \
        "신호를 점수로 합치면 근거가 사라진다 — 근거 없는 순위는 광고와 같다"
    for spec in shopping.TRUST_SIGNALS.values():
        assert spec.get("label") and spec.get("desc"), "신호가 자기를 설명하지 못한다"


# ── ④ 가격 변동 ────────────────────────────────────────────────────────────

def test_a_meaningful_drop_is_reported():
    got = price_change(289000, 277000)
    assert got["changed"] and got["direction"] == "down" and got["delta"] == -12000


def test_a_tiny_wobble_is_not_news():
    """★소음이 쌓이면 사람은 알림을 끈다★ 100원 차이를 알리는 것은 도움이 아니다."""
    assert price_change(289000, 288900)["changed"] is False


def test_a_rise_is_reported_too():
    """오른 것도 말해야 한다 — "지금 사면 손해"가 사용자에게 더 중요할 수 있다."""
    got = price_change(100000, 110000)
    assert got["changed"] and got["direction"] == "up"


def test_an_unknown_price_is_not_a_change():
    assert price_change(0, 50000)["changed"] is False
    assert price_change(50000, 0)["changed"] is False


# ── ⑤ 같은 상품 묶기 ───────────────────────────────────────────────────────

def test_the_same_product_from_different_sellers_is_one_thing():
    """판매처마다 제목에 온갖 수식이 붙는다 — 안 묶으면 "여러 곳에서 파는 하나"가
    네 개의 후보로 보인다."""
    a = _c("[무료배송] 소니 WF-1000XM5 정품 ★당일발송★", 289000, seller="A")
    b = _c("소니 WF-1000XM5", 279000, seller="B")
    assert a.key() == b.key(), f"{a.key()!r} != {b.key()!r}"


def test_different_products_stay_different():
    assert _c("소니 WF-1000XM5").key() != _c("소니 WF-1000XM4").key()


# ── ⑥ 두 번째 실행 — ★이 페이즈의 심장★(Sean 요구 6) ───────────────────────

from shopping_core import compare_with_past   # noqa: E402


def test_the_first_time_is_told_apart_from_a_repeat():
    """처음 보는 물건에 "지난번에…"라고 하면 그것은 거짓말이다."""
    assert compare_with_past({}, [_c("A", 1000)])["first_time"] is True


def test_a_price_drop_since_last_time_is_the_headline(brain):
    """★*"지난주에 망설이던 그 이어폰, 12,000원 내렸어요"*★ 이것이 만들려는 것이다."""
    remember_search(brain, USER, "무선 이어폰", [_c("소니 WF-1000XM5", 289000)])
    past = recall_search(brain, USER, "무선 이어폰")

    got = compare_with_past(past, [_c("소니 WF-1000XM5", 277000)])
    assert got["first_time"] is False
    assert got["changes"][0]["delta"] == -12000
    assert got["changes"][0]["direction"] == "down"


def test_the_biggest_move_comes_first(brain):
    """화면도 말도 **가장 중요한 것부터** 나와야 한다."""
    remember_search(brain, USER, "이어폰", [_c("A", 100000), _c("B", 100000)])
    past = recall_search(brain, USER, "이어폰")
    got = compare_with_past(past, [_c("A", 95000), _c("B", 70000)])
    assert [c["title"] for c in got["changes"]] == ["B", "A"]


def test_something_that_disappeared_is_reported(brain):
    """품절·단종일 수 있다 — 조용히 빠지면 사용자는 자기가 잘못 본 줄 안다."""
    remember_search(brain, USER, "이어폰", [_c("있던 것", 1000), _c("남은 것", 2000)])
    past = recall_search(brain, USER, "이어폰")
    got = compare_with_past(past, [_c("남은 것", 2000)])
    assert got["gone"] == ["있던 것"]


def test_a_newly_appearing_option_is_reported(brain):
    remember_search(brain, USER, "이어폰", [_c("기존", 1000)])
    past = recall_search(brain, USER, "이어폰")
    got = compare_with_past(past, [_c("기존", 1000), _c("새것", 900)])
    assert got["new"] == ["새것"]


def test_a_very_old_search_is_not_called_last_time(brain):
    """★반 년 전 것을 들이밀면 도움이 아니라 참견이다★"""
    remember_search(brain, USER, "이어폰", [_c("A", 1000)],
                    now="2026-01-01T10:00:00")
    past = recall_search(brain, USER, "이어폰")
    got = compare_with_past(past, [_c("A", 1000)], now="2026-08-03T10:00:00")
    assert got["stale"] is True, "오래된 검색을 '지난번'으로 들이민다"

    recent = compare_with_past(past, [_c("A", 1000)], now="2026-01-20T10:00:00")
    assert recent["stale"] is False


def test_whether_it_was_bought_is_never_guessed(brain):
    """★추측해서 상태를 바꾸면 그것이 곧 오염이다★ 결제를 우리가 하지 않는 한
    알 방법이 없다 — 그래서 **묻는다**(Phase W가 서면 그때는 안다)."""
    remember_search(brain, USER, "이어폰", [_c("A", 1000)])
    past = recall_search(brain, USER, "이어폰")
    got = compare_with_past(past, [])
    assert "bought" not in got, "샀는지를 추측했다"
    # ★이 줄은 원래 정반대를 지키고 있었다★ — `item == {"A"}`를 요구하면서 주석에는
    # *"후보가 소유물로 옮겨졌다"* 라고 적혀 있었다. 테스트가 결함을 **굳히고**
    # 있었던 것이다(K2-0 실측). 사지 않은 것은 소유물에 없어야 한다.
    assert brain.find_entities(USER, kind="item") == [], "사지 않았는데 소유물이 됐다"
    assert {e.name for e in brain.find_entities(USER, kind="product")} == {"A"}


def test_prices_that_did_not_really_move_are_not_reported(brain):
    """소음이 쌓이면 사람은 알림을 끈다."""
    remember_search(brain, USER, "이어폰", [_c("A", 289000)])
    past = recall_search(brain, USER, "이어폰")
    assert compare_with_past(past, [_c("A", 288900)])["changes"] == []


# ── ⑦ ★결제까지 갔다는 사실★ — ③의 재료다 ─────────────────────────────────

def test_cheapest_is_judged_over_the_whole_list_not_a_page():
    """★한 쪽만 보고 정하면 거짓말이 된다★ 판정은 **전체를 아는 쪽**이 한다."""
    rows = [{"price": 20_000}, {"price": 0}, {"price": 15_000}, {"price": 18_000}]
    assert shopping.cheapest_index(rows) == 2
    # 값을 모르는 것(0)은 "공짜"가 아니다 — 가장 싼 것으로 뽑히면 안 된다
    assert shopping.cheapest_index([{"price": 0}, {"price": 0}]) == -1
    assert shopping.cheapest_index([]) == -1
    # 같은 값이면 앞의 것(순위가 이미 정렬해 두었다)
    assert shopping.cheapest_index([{"price": 100}, {"price": 100}]) == 0


def test_going_to_checkout_is_remembered_but_not_as_a_purchase(tmp_path):
    """★"갔다"까지만 적는다★ 우리가 결제를 실행하지 않으므로 샀는지는 알 수 없다 —
    추측해서 상태를 바꾸면 그것이 곧 오염이다. 샀는지는 다음번에 **묻는다**.

    그리고 이것이 *"값이 내리면 알린다"* 의 재료다: 아직 안 샀고 사려는 마음이
    남아 있는 것을 가리려면, 어디까지 갔는지가 기억에 있어야 한다.
    """
    from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
    brain = LiteMemoryProvider(tmp_path / "brain")
    shopping.remember_search(brain, "u1", "무선 이어폰",
                             [_c("소니 WF-1000XM5", 289_000, rating=4.6)])

    got = shopping.remember_checkout(brain, "u1", "무선 이어폰",
                                     "소니 WF-1000XM5", "sony.co.kr")
    assert got, "결제까지 간 사실이 안 남았다"

    entities, _ = brain.export_graph("u1", limit=200)
    node = next(e for e in entities if e.name == "소니 WF-1000XM5")
    assert node.attrs.get("checkout_at"), "언제 갔는지가 없다"
    assert node.attrs.get("checkout_origin") == "sony.co.kr"
    # ★사람이 누른 것이다★ 자동 파이프라인이 덮으면 안 된다
    assert node.attrs.get("provenance") == "user"
    assert "bought" not in node.attrs and "purchased" not in node.attrs, \
        "★샀다고 적었다 — 우리는 그것을 알 수 없다★"


def test_a_checkout_for_something_never_searched_is_not_invented(tmp_path):
    """의도(`wish`)가 없으면 붙일 자리가 없다 — 없는 자리에 새로 만들지 않는다."""
    from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
    brain = LiteMemoryProvider(tmp_path / "brain")
    assert shopping.remember_checkout(brain, "u1", "찾은 적 없는 것", "X", "x.com") == ""
