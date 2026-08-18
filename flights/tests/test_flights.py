"""항공권 에이전트(Phase MA ⑥) — ★두 번째 검색이 값어치다★.

이 파일이 지키는 것 여섯:

  ① ★"지난주에 보던 그 노선, 8만원 내렸다"★ 남기지 않으면 이 기능은 검색창 하나
     더에 지나지 않는다(원칙 0 ③)
  ② ★값을 모르는 것을 공짜로 읽지 않는다★ 0을 최저가로 두면 값 없는 항공편이
     추천 1순위가 된다
  ③ 판정은 **우리 코드**가 한다 — 모델은 옮기기만. 모델이 판정하면 매번 기준이
     달라지고 아무도 설명할 수 없다
  ④ 지어내지 않는다 — 못 찾으면 못 찾았다고, 처음이면 "지난번" 이야기를 안 한다
  ⑤ 지난 검색이 너무 오래됐으면 **들이밀지 않는다**(참견이 된다)
  ⑥ 검색어도 **언어를 탄다** — 영어 낱말을 박으면 다른 언어 사용자가 엉뚱한 결과를 받는다
"""
from __future__ import annotations

import json

import pytest

import flights_scout as core
from cosmos.contracts.memory import Entity
from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
from flights_scout import FlightsPlugin

_ROWS = json.dumps([
    {"airline": "Korean Air", "origin": "ICN", "destination": "Tokyo",
     "depart": "2026-09-10", "stops": 0, "price": 380000, "currency": "KRW",
     "url": "https://example.com/a", "note": "morning departure"},
    {"airline": "Peach", "origin": "ICN", "destination": "Tokyo",
     "depart": "2026-09-10", "stops": 1, "price": 210000, "currency": "KRW",
     "url": "https://example.com/b"},
    {"airline": "Mystery Air", "origin": "ICN", "destination": "Tokyo",
     "stops": 0, "price": 0, "currency": "KRW"},
])


class _Ctx:
    def __init__(self, brain=None, *, search="results", extract=_ROWS, home=None):
        self.brain = brain
        self.user_id = "u1"
        self.logs: list[str] = []
        self.tool_calls: list[tuple] = []
        self.notices: dict[str, dict] = {}
        self.cleared: list[str] = []
        self._search = search
        self._extract = extract
        self._home = home

    # ★화면 상태의 자리★ 없으면 `_remember_view`가 조용히 실패하고, 그러면 화면을
    # 검사하는 그물이 **빈 화면을 보고도 통과한다**.
    def data_dir(self, component):
        import pathlib
        import tempfile
        base = pathlib.Path(self._home or tempfile.gettempdir())
        path = base / "agentdata" / component
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_log(self, message, speaker=None, level="info"):
        self.logs.append(message)

    def run_tool(self, name, args):
        self.tool_calls.append((name, args))
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


# ── 노선 이름 — 기억을 합치는 열쇠 ───────────────────────────────────────────

@pytest.mark.parametrize("origin,destination,expected", [
    ("ICN", "NRT", "Flights ICN to NRT"),
    ("seoul", "tokyo", "Flights Seoul to Tokyo"),
    ("", "tokyo", "Flights to Tokyo"),
    ("", "", ""),
])
def test_a_route_has_one_name(origin, destination, expected):
    """★이름이 갈리면 같은 노선을 두 곳에 쌓는다★ — 그러면 비교가 영영 안 된다."""
    assert core.route_name(origin, destination) == expected


def test_the_same_route_written_differently_still_matches(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "seoul", "tokyo", [])
    assert core.recall_route(brain, "u1", "Seoul", "TOKYO")["route"] == \
        "Flights Seoul to Tokyo"


# ── ③ 정규화 ────────────────────────────────────────────────────────────────

def test_the_model_only_moves_things_across():
    flights = core.to_flights(_ROWS)
    assert [f.airline for f in flights] == ["Korean Air", "Peach", "Mystery Air"]
    assert flights[0].stops == 0 and flights[0].price == 380000


def test_broken_rows_are_dropped_not_fatal():
    """★한 줄이 이상하다고 검색 전체를 실패로 만들면 아무것도 못 본다★"""
    assert core.to_flights("not json") == []
    assert core.to_flights(json.dumps([{"airline": "No destination"}])) == []
    assert core.to_flights(json.dumps(["junk", {"destination": "Tokyo"}])) != []
    assert core.to_flights(None) == []


def test_a_negative_or_silly_price_becomes_unknown():
    rows = json.dumps([{"destination": "Tokyo", "price": -5},
                       {"destination": "Tokyo", "price": "cheap"}])
    assert [f.price for f in core.to_flights(rows)] == [0, 0]


# ── ② 순위 ───────────────────────────────────────────────────────────────────

def test_cheapest_first_then_fewest_stops():
    """★그런데 **맨 앞은 값이 아니라 미는 것**이다★ (2026-08-19 · 찍어 보고 고쳤다)

    값순 1번을 그대로 밀었더니 *"추천"* 이 **13시간 걸리고 두 번 갈아타는** 표에
    붙었다. 물건은 싼 것이 대체로 좋은 것이지만 ★표는 싼 것이 대체로 고된 것★이다.
    """
    flights = core.rank(core.to_flights(_ROWS))
    # Korean Air 는 직항 380,000 · Peach 는 1회 경유 210,000
    assert flights[0].airline == "Korean Air"
    # 뒤는 값순 그대로다 — 그리고 값 모르는 것은 여전히 맨 뒤다
    assert [f.airline for f in flights[1:]] == ["Peach", "Mystery Air"]


def test_the_one_we_push_is_the_cheapest_of_the_easiest():
    """★점수로 합치지 않는다★ 값과 시간을 버무리면 근거가 사라지고, 근거 없는
    순위는 광고와 구별되지 않는다. 대신 **말할 수 있는 규칙 하나**를 쓴다."""
    flights = core.to_flights(_ROWS)
    pick = core.best_pick(flights)
    assert pick.airline == "Korean Air" and pick.stops == 0
    # ★값을 모르는 것을 밀지 않는다★ 사용자는 눌러 보고서야 알게 된다
    assert pick.price > 0
    assert core.best_pick([]) is None
    assert core.best_pick(core.to_flights(
        json.dumps([{"destination": "Tokyo", "airline": "No price"}]))) is None


def test_the_push_says_why_it_is_the_push():
    """★이유 없는 순위는 광고와 구별되지 않는다★"""
    flights = core.to_flights(_ROWS)
    reason = core.pick_reason(flights, core.best_pick(flights))
    assert "Nonstop" in reason
    # 미는 것이 마침 가장 싸면 이유를 따로 대지 않는다 — 값이 이미 보인다
    easy = core.to_flights(json.dumps([_row("Peach", 100_000, stops=0),
                                       _row("Other", 200_000, stops=1)]))
    assert core.pick_reason(easy, core.best_pick(easy)) == ""


def test_an_unknown_price_never_wins():
    """★0을 '공짜'로 읽으면 값 모르는 항공편이 추천 1순위가 된다★"""
    ranked = core.rank(core.to_flights(_ROWS))
    assert ranked[-1].airline == "Mystery Air"
    assert core.cheapest(core.to_flights(_ROWS)).airline == "Peach"


def test_with_no_prices_at_all_there_is_no_cheapest():
    rows = json.dumps([{"destination": "Tokyo"}, {"destination": "Tokyo"}])
    assert core.cheapest(core.to_flights(rows)) is None


def test_the_list_is_capped():
    rows = json.dumps([{"destination": "Tokyo", "airline": f"A{i}", "price": i + 1}
                       for i in range(30)])
    assert len(core.rank(core.to_flights(rows))) == core.MAX_KEPT


# ── ①④⑤ 지난번과 비교 ───────────────────────────────────────────────────────

def test_the_first_time_there_is_no_last_time():
    diff = core.compare_with_past({}, core.to_flights(_ROWS))
    assert diff["first_time"] is True and diff["delta"] is None


def test_a_fare_that_dropped_is_the_headline():
    """★이 검사가 이 에이전트의 값어치다★"""
    past = {"price": 290000, "seen_at": core.now_ts()}
    diff = core.compare_with_past(past, core.to_flights(_ROWS))
    assert diff["delta"] == 210000 - 290000
    line = core.headline("Flights ICN to Tokyo", core.rank(core.to_flights(_ROWS)), diff)
    assert "down 80,000" in line and line.startswith("That route is down")


def test_a_fare_that_rose_says_so_too():
    past = {"price": 100000, "seen_at": core.now_ts()}
    diff = core.compare_with_past(past, core.to_flights(_ROWS))
    assert diff["delta"] == 110000
    assert "up 110,000" in core.headline("r", core.rank(core.to_flights(_ROWS)), diff)


def test_a_search_from_long_ago_is_not_pushed_at_you():
    """★반 년 전 한 번 본 것을 들이밀면 도움이 아니라 참견이다★"""
    past = {"price": 290000, "seen_at": "2020-01-01T00:00:00+00:00"}
    diff = core.compare_with_past(past, core.to_flights(_ROWS))
    assert diff["stale"] is True and diff["delta"] is None
    assert "been a while" in core.headline("r", core.rank(core.to_flights(_ROWS)), diff)


def test_nothing_found_says_nothing_found():
    assert "found nothing" in core.headline("Flights to Tokyo", [], {})


# ── 기억 (원칙 0) ────────────────────────────────────────────────────────────

def test_a_search_leaves_the_intent_and_the_place(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", core.to_flights(_ROWS))
    wishes = {e.name: e for e in brain.find_entities("u1", kind="wish")}
    places = [e.name for e in brain.find_entities("u1", kind="place")]
    assert "Flights ICN to Tokyo" in wishes
    assert "Tokyo" in places
    # ★가격은 **관측으로** 남는다 — 시각과 함께라 나중에도 참이다★
    assert wishes["Flights ICN to Tokyo"].attrs["price"] == 210000
    assert wishes["Flights ICN to Tokyo"].attrs["seen_at"]


def test_searching_twice_updates_one_route_not_two(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", core.to_flights(_ROWS))
    cheaper = json.dumps([{"airline": "Peach", "destination": "Tokyo",
                           "price": 150000, "currency": "KRW"}])
    core.remember_search(brain, "u1", "ICN", "Tokyo", core.to_flights(cheaper))
    routes = [e for e in brain.find_entities("u1", kind="wish")]
    assert len(routes) == 1
    assert core.recall_route(brain, "u1", "ICN", "Tokyo")["price"] == 150000


def test_a_route_never_searched_is_not_invented(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    assert core.recall_route(brain, "u1", "ICN", "Paris") == {}
    assert core.recall_route(None, "u1", "a", "b") == {}
    assert core.tracked_routes(brain, "u1") == []


def test_shopping_wishes_do_not_show_up_as_trips(tmp_path):
    """★`wish`는 쇼핑도 쓴다★ 목적지가 없는 위시를 여행으로 세면
    *"어디 가려 했지"* 에 이어폰이 나온다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    brain.upsert_entity("u1", Entity(name="Wireless earbuds", kind="wish"))
    core.remember_search(brain, "u1", "ICN", "Tokyo", core.to_flights(_ROWS))
    assert [r["destination"] for r in core.tracked_routes(brain, "u1")] == ["Tokyo"]


def test_the_whole_road_from_search_to_the_next_search(tmp_path):
    """★저장 → 되읽기 → 비교★ 한 길을 통째로 지난다(원칙 0 ①→③)."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    plugin.run(_Ctx(brain=brain), action="search", origin="ICN", destination="Tokyo")

    cheaper = json.dumps([{"airline": "Peach", "origin": "ICN",
                           "destination": "Tokyo", "price": 150000,
                           "currency": "KRW", "stops": 1}])
    answer = plugin.run(_Ctx(brain=brain, extract=cheaper), action="search",
                        origin="ICN", destination="Tokyo")
    assert "down 60,000 KRW" in answer


def test_a_broken_brain_still_returns_the_flights(tmp_path):
    class _Broken:
        def find_entities(self, *a, **k):
            raise RuntimeError("brain is down")

        def __getattr__(self, name):
            raise RuntimeError("brain is down")

    ctx = _Ctx(brain=_Broken())
    answer = FlightsPlugin().run(ctx, action="search", destination="Tokyo")
    assert "Peach" in answer
    assert any("could not remember" in line for line in ctx.logs)


def test_forgetting_a_route_stops_the_tracking(tmp_path):
    """★사용자의 결정이 이긴다★"""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    plugin.run(_Ctx(brain=brain), action="search", origin="ICN", destination="Tokyo")
    assert core.tracked_routes(brain, "u1")

    answer = plugin.run(_Ctx(brain=brain), action="forget", origin="ICN",
                        destination="Tokyo")
    assert "stop tracking" in answer
    assert core.tracked_routes(brain, "u1") == []


def test_forgetting_something_never_tracked_says_so(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    answer = FlightsPlugin().run(_Ctx(brain=brain), action="forget",
                                 destination="Paris")
    assert "was not tracking" in answer


def test_plans_lists_what_you_were_looking_at(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    plugin.run(_Ctx(brain=brain), action="search", origin="ICN", destination="Tokyo")
    answer = plugin.run(_Ctx(brain=brain), action="plans")
    assert "Flights ICN to Tokyo" in answer and "210,000 KRW" in answer


def test_plans_with_nothing_says_nothing(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    assert "not looked at any" in FlightsPlugin().run(_Ctx(brain=brain), action="plans")


# ── ⑥ 검색과 언어 ────────────────────────────────────────────────────────────

def test_the_search_terms_go_through_translation(monkeypatch):
    """★기능 문자열도 언어를 탄다★ 영어를 박으면 한국어 사용자가 엉뚱한 결과를 받는다."""
    seen = {}
    monkeypatch.setattr(core.i18n, "t",
                        lambda text, **kw: seen.setdefault("asked", text) and text)
    ctx = _Ctx()
    FlightsPlugin().run(ctx, action="search", origin="ICN", destination="Tokyo")
    assert seen["asked"] == "flight ticket price"
    assert "flight ticket price" in ctx.tool_calls[0][1]["query"]


def test_the_query_carries_the_route_and_the_date():
    ctx = _Ctx()
    FlightsPlugin().run(ctx, action="search", origin="ICN", destination="Tokyo",
                        depart="2026-09-10")
    query = ctx.tool_calls[0][1]["query"]
    assert "ICN" in query and "Tokyo" in query and "2026-09-10" in query


def test_flights_to_somewhere_else_are_dropped(tmp_path):
    """★모델이 엉뚱한 노선을 섞어 오면 버린다★ — 우리가 물은 곳만 남긴다.

    ⚠️ ★답에 목적지가 안 실린다★ 처음에는 답에서 `"Osaka"`를 찾았는데, 답은
    항공사·가격·경유만 적으므로 **언제나 통과했다**. 걸러졌는지는 **항공사 이름**과
    **개수**로 봐야 한다(함정 15).
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    mixed = json.dumps([{"airline": "Osaka Air", "destination": "Osaka", "price": 100},
                        {"airline": "Tokyo Air", "destination": "Tokyo", "price": 200}])
    ctx = _Ctx(brain=brain, extract=mixed)
    answer = FlightsPlugin().run(ctx, action="search", destination="Tokyo")
    assert "Tokyo Air" in answer and "Osaka Air" not in answer


def test_when_everything_is_off_route_we_still_show_something():
    """★전부 걸러지면 빈손이 된다★ — 그때는 우리가 모델보다 낫다고 우기지 않고
    찾아온 것을 보여 준다(빈 화면보다는 낫고, 판정은 사람이 한다)."""
    off = json.dumps([{"airline": "Osaka Air", "destination": "Osaka", "price": 100}])
    answer = FlightsPlugin().run(_Ctx(extract=off), action="search",
                                 destination="Tokyo")
    assert "Osaka Air" in answer


def test_an_unknown_action_falls_back_to_searching(tmp_path):
    """★모르는 말은 **읽는 쪽**으로 떨어진다★ — 짐작으로 추적을 지우지 않는다.

    ⚠️ 이 갈래를 안 재고 있어서, 폴백을 `forget`으로 바꾸는 뮤테이션이 빠져나갔다.
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    plugin.run(_Ctx(brain=brain), action="search", origin="ICN", destination="Tokyo")
    answer = plugin.run(_Ctx(brain=brain), action="book it now", origin="ICN",
                        destination="Tokyo")
    assert "Peach" in answer                       # 검색이 돌았다
    assert core.tracked_routes(brain, "u1")        # 추적이 지워지지 않았다


def test_without_a_destination_it_asks():
    assert "where you want to fly" in FlightsPlugin().run(_Ctx(), action="search")


def test_a_failed_web_search_does_not_pretend():
    class _NoSearch(_Ctx):
        def run_tool(self, name, args):
            raise RuntimeError("network down")

    answer = FlightsPlugin().run(_NoSearch(), action="search", destination="Tokyo")
    assert "could not find" in answer


def test_the_declared_actions_and_the_table_are_the_same_list():
    described = FlightsPlugin().parameters["properties"]["action"]["description"]
    for name in core.ACTIONS:
        assert name in described


# ══ Phase AG ①-2d — ★날짜 · 결과 · 알림 · 화면★ ═══════════════════════════════
#
# 이 아래가 지키는 것 다섯:
#
#   ⑦ ★같은 노선도 **다른 날은 다른 것**이다★ 물건에는 없는 축이고, 이것을 뭉개면
#      12월 표 한 번이 9월 표의 기억을 덮고 **없던 인상**을 말한다
#   ⑧ ★묻기만 하고 답을 안 적으면 열 번을 물어도 매번 처음이다★ — 그리고 무엇보다
#      끊은 사람에게도 *"더 싸졌어요"* 라고 말하게 된다
#   ⑨ ★알림은 화면보다 문턱이 높다★ 그리고 **해소되면 스스로 내려간다**
#   ⑩ 판정은 **전체를 아는 쪽**이 한다 — 화면이 받은 한 쪽에서 고르면 거짓말이 된다
#   ⑪ ★떠난 비행기는 지켜보지 않는다★ 값이 내려도 아무 값이 없다

from cosmos.contracts import hooks as _hooks
from cosmos.contracts.view import COMPARE_SIGNALS as _SIGNALS
from cosmos.contracts.view import normalize as _normalize


def _flights(*rows):
    return core.to_flights(json.dumps(list(rows)))


def _row(airline, price, **kw):
    return {"airline": airline, "origin": "ICN", "destination": "Tokyo",
            "price": price, "currency": "KRW", **kw}


# ── ⑦ 날짜가 노선을 가른다 ───────────────────────────────────────────────────

def test_the_same_route_on_another_date_is_another_trip():
    """★물건에는 없는 축이다★ 9월 10일 도쿄행과 12월 24일 도쿄행은 다른 것이다."""
    september = core.route_name("ICN", "Tokyo", "2026-09-10")
    december = core.route_name("ICN", "Tokyo", "2026-12-24")
    assert september != december
    assert "2026-09-10" in september
    # 날짜를 안 말했으면 이름에도 없다 — 그것은 *"언젠가 도쿄"* 라는 다른 의도다
    assert core.route_name("ICN", "Tokyo") == "Flights ICN to Tokyo"


def test_a_date_we_cannot_read_is_not_half_used():
    """★반쯤 읽어 이름에 끼우면 같은 날이 두 이름으로 갈린다★"""
    assert core.route_name("ICN", "Tokyo", "next month") == "Flights ICN to Tokyo"
    assert core.route_name("ICN", "Tokyo", "2026-09") == "Flights ICN to Tokyo"


def test_december_prices_do_not_overwrite_september_prices(tmp_path):
    """★이것이 날짜를 이름에 넣은 이유다★

    예전에는 노선 이름에 날짜가 없어서, 성수기 표를 한 번 찾아본 것이 비수기 표의
    기억을 덮었다. 그리고 그다음 검색이 *"74만원 올랐어요"* 라고 **일어나지 않은
    인상**을 말했다.
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo",
                         _flights(_row("Peach", 210_000)), depart="2026-09-10")
    core.remember_search(brain, "u1", "ICN", "Tokyo",
                         _flights(_row("Korean Air", 950_000)), depart="2026-12-24")

    cheap = core.recall_route(brain, "u1", "ICN", "Tokyo", "2026-09-10")
    peak = core.recall_route(brain, "u1", "ICN", "Tokyo", "2026-12-24")
    assert cheap["price"] == 210_000, "성수기 검색이 비수기 기억을 덮었습니다"
    assert peak["price"] == 950_000
    assert len(brain.find_entities("u1", kind="wish")) == 2


# ── ⑪ 떠난 비행기 ────────────────────────────────────────────────────────────

def test_a_plane_that_already_left_is_not_watched():
    """★값이 내려도 아무 값이 없다★ 물건에는 이런 끝이 없다."""
    assert core.has_flown("2020-01-01")
    assert not core.has_flown("2099-01-01")
    # ★날짜를 모르면 떠나지 않은 것으로 본다★ 모른다고 지우면 날짜 없이 찾아본
    # 의도가 통째로 사라진다
    assert not core.has_flown("")
    assert not core.still_wanted({"seen_at": core.now_ts(), "depart": "2020-01-01"})
    assert core.still_wanted({"seen_at": core.now_ts(), "depart": "2099-01-01"})


# ── ⑧ 답을 적는다 ────────────────────────────────────────────────────────────

def test_the_watchlist_only_holds_what_is_still_open(tmp_path):
    """★되읽는 문★ 이것이 없으면 `remember_outcome`은 쌓기만 하고 쓰는 곳이 없다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 210_000)))
    core.remember_search(brain, "u1", "ICN", "Osaka",
                         _flights(_row("Peach", 180_000, destination="Osaka")))
    assert len(core.watchlist(brain, "u1")) == 2

    core.remember_outcome(brain, "u1", "Flights ICN to Tokyo", "booked")
    assert [r["destination"] for r in core.watchlist(brain, "u1")] == ["Osaka"]


def test_saying_you_have_not_booked_after_all_puts_it_back(tmp_path):
    """★못 되돌리는 기록은 사람이 말하기를 망설이게 만든다★"""
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 210_000)))
    core.remember_outcome(brain, "u1", "Flights ICN to Tokyo", "booked")
    assert not core.watchlist(brain, "u1")
    core.remember_outcome(brain, "u1", "Flights ICN to Tokyo", "")
    assert len(core.watchlist(brain, "u1")) == 1


def test_the_decision_is_the_users_and_cannot_be_overwritten(tmp_path):
    """★사용자 발화·결정이 언제나 이긴다★ 어떤 자동 파이프라인도 못 덮는다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 210_000)))
    core.remember_outcome(brain, "u1", "Flights ICN to Tokyo", "dropped")
    node = next(e for e in brain.find_entities("u1", kind="wish"))
    assert node.attrs.get("provenance") == "user" and node.attrs.get("dropped_at")


def test_a_booked_trip_is_never_told_it_got_cheaper(tmp_path):
    """★끊고 나서 "더 싸졌어요"는 도움이 아니라 상처다★"""
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 290_000)))
    core.remember_outcome(brain, "u1", "Flights ICN to Tokyo", "booked")
    past = core.recall_route(brain, "u1", "ICN", "Tokyo")
    diff = core.compare_with_past(past, _flights(_row("Peach", 190_000)))
    assert diff["booked"] is True
    line = core.headline("Flights ICN to Tokyo",
                         core.rank(_flights(_row("Peach", 190_000))), diff)
    assert "cheaper" not in line and "down" not in line
    assert "booked" in line


def test_saying_i_booked_it_out_loud_is_written_down(tmp_path):
    """*"끊었나요?"* 의 답이 **어딘가에 남아야** 다음번에 안 묻는다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    ctx = _Ctx(brain=brain, home=tmp_path)
    plugin.run(ctx, action="search", origin="ICN", destination="Tokyo")
    assert core.watchlist(brain, "u1")

    # ★노선을 다시 안 댄다★ 사람은 *"응 끊었어"* 라고만 한다 — 방금 보던 것이
    # 무엇인지는 화면 상태가 안다
    answer = plugin.run(ctx, action="booked")
    assert "booked" in answer
    assert not core.watchlist(brain, "u1")


def test_a_background_check_keeps_everything_else_the_wish_knows(tmp_path):
    """★적을 것만 넘기면 나머지가 지워진다★ (쇼핑에서 실측으로 잡은 결함이다)

    `update_entity`는 attrs를 병합하지 않고 **통째로 갈아 끼운다**. 적을 것만
    넘기면 값·통화·마지막 알림 시각·`provenance=user`가 전부 사라지고, 그러면
    이 기능이 서 있는 바닥이 무너진다.
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 210_000)))
    row = core.watchlist(brain, "u1")[0]
    before = dict(brain.get_entity("u1", row["wish_id"]).attrs or {})
    assert before.get("provenance") == "user", "★측정 무효★ 잴 것이 애초에 없습니다"

    core.remember_check(brain, "u1", row["wish_id"])

    after = dict(brain.get_entity("u1", row["wish_id"]).attrs or {})
    assert after.get("last_checked"), "점검한 시각을 안 적었습니다"
    lost = sorted(k for k in before if k not in after)
    assert not lost, f"점검이 이 노선이 알던 것을 지웠습니다: {lost}"


# ── 값 흐름 — ★관측은 쌓인다★ ────────────────────────────────────────────────

def test_the_fare_trend_is_built_from_observations(tmp_path):
    """★마지막 값 하나만 남기면 "어느 쪽으로 가고 있나"를 못 말한다★

    사람이 표를 살 때 실제로 묻는 것은 *"더 기다리면 더 내릴까"* 다.
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    for price in (290_000, 260_000, 210_000):
        core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", price)))
    history = core.recall_route(brain, "u1", "ICN", "Tokyo")["history"]
    assert [p["price"] for p in history] == [290_000, 260_000, 210_000]


def test_the_same_fare_twice_does_not_add_a_point():
    """★반나절마다 같은 값을 찍으면 선은 평평한데 점만 스물넷이 된다★"""
    rows = core._extend_history([], "2026-08-01T00:00:00", 210_000)
    rows = core._extend_history(rows, "2026-08-02T00:00:00", 210_000)
    assert len(rows) == 1 and rows[0]["ts"] == "2026-08-02T00:00:00"
    rows = core._extend_history(rows, "2026-08-03T00:00:00", 190_000)
    assert len(rows) == 2


def test_the_trend_does_not_grow_forever():
    rows = []
    for n in range(100):
        rows = core._extend_history(rows, f"2026-08-01T00:{n:02d}:00", 1000 + n)
    assert len(rows) == core.MAX_HISTORY


# ── ⑨ 알림 ───────────────────────────────────────────────────────────────────

def test_the_hook_is_declared_so_the_user_can_turn_it_off():
    """★끄면 정말로 안 불려야 한다★ 선언이 없으면 코스모스가 부를 수도, 끌 수도 없다."""
    assert FlightsPlugin.raises_notices is True
    assert hasattr(FlightsPlugin, _hooks.HOOKS["notice"]["method"])
    assert "notice" in _hooks.declared(FlightsPlugin)


def test_the_bar_for_interrupting_is_higher_than_the_bar_for_the_screen():
    """★화면은 지나가다 보는 것이고 알림은 하던 일을 멈추게 하는 것이다★"""
    assert core.ALERT_MIN_RATIO > core.PRICE_CHANGE_MIN_RATIO


def test_a_real_drop_is_worth_saying():
    got = core.worth_interrupting(500_000, 400_000, currency="KRW")
    assert got["tell"] and got["reason"] == "cheaper"


def test_a_small_wobble_is_not():
    """500,000 → 490,000 은 2%다 — 화면에는 그리지만 말을 걸지는 않는다."""
    assert not core.worth_interrupting(500_000, 490_000, currency="KRW")["tell"]


def test_a_fare_going_up_is_never_an_interruption():
    """★"12만원 올랐어요"로 표를 살 수 있는 사람은 없다★"""
    assert not core.worth_interrupting(400_000, 500_000, currency="KRW")["tell"]


def test_the_floor_is_not_written_in_won_for_everybody():
    """★통화마다 다르다★ 원 기준 금액을 박아 두면 달러로 파는 표는 **$20,000이
    내려야** 말을 건다 — CLAUDE.md가 못 박은 자리 그대로다."""
    assert core.alert_floor("KRW") != core.alert_floor("USD")
    # 690 → 590 USD 는 14% · 100달러 — 말할 만하다
    assert core.worth_interrupting(690, 590, currency="USD")["tell"]
    # 같은 숫자를 원으로 보면 문턱에 한참 못 미친다
    assert not core.worth_interrupting(690, 590, currency="KRW")["tell"]


def test_an_unknown_currency_is_judged_by_ratio_alone():
    """★아무 숫자나 기본값으로 두면 그 통화 사용자에게는 엉뚱한 문턱이 선다★"""
    assert core.alert_floor("XYZ") == 0
    assert core.worth_interrupting(100, 80, currency="XYZ")["tell"]


def test_the_same_route_is_not_raised_two_days_running():
    assert not core.worth_interrupting(
        500_000, 400_000, currency="KRW",
        last_alert="2026-08-18T09:00:00", now="2026-08-18T21:00:00")["tell"]
    assert core.worth_interrupting(
        500_000, 400_000, currency="KRW",
        last_alert="2026-08-01T09:00:00", now="2026-08-18T21:00:00")["tell"]


def test_never_checked_means_check_now():
    """★빈 값을 "방금 봤다"로 읽으면 영영 안 본다★"""
    assert core.due_for_recheck("")
    assert core.due_for_recheck("this is not a time")
    assert not core.due_for_recheck("2026-08-18T09:00:00", now="2026-08-18T10:00:00")
    assert core.due_for_recheck("2026-08-17T09:00:00", now="2026-08-18T10:00:00")


def test_a_fare_drop_actually_raises_a_notice(tmp_path):
    """★배선까지 잰다★ 판정 함수만 검사하면 `advise()`가 비어 있어도 초록이다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 290_000)))

    ctx = _Ctx(brain=brain, home=tmp_path, extract=json.dumps([_row("Peach", 190_000)]))
    plugin.advise(ctx)
    assert ctx.notices, "값이 내렸는데 아무 말도 안 했습니다"
    said = next(iter(ctx.notices.values()))
    assert "100,000 KRW" in said["title"], said["title"]


def test_nothing_is_said_about_a_trip_already_booked(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 290_000)))
    core.remember_outcome(brain, "u1", "Flights ICN to Tokyo", "booked")
    ctx = _Ctx(brain=brain, home=tmp_path, extract=json.dumps([_row("Peach", 190_000)]))
    FlightsPlugin().advise(ctx)
    assert not ctx.notices


def test_a_fare_in_another_currency_is_not_compared(tmp_path):
    """★89만 KRW와 690 USD를 빼면 그 숫자는 아무 뜻이 없다★

    그리고 그 숫자로 *"내렸다"* 고 말하면 그것은 거짓말이다.
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 890_000)))
    ctx = _Ctx(brain=brain, home=tmp_path,
               extract=json.dumps([dict(_row("Peach", 690), currency="USD")]))
    FlightsPlugin().advise(ctx)
    assert not ctx.notices, "통화가 다른 값을 견줘 알렸습니다"


def test_the_notice_comes_down_by_itself_once_it_is_booked(tmp_path):
    """★내려가지 않는 알림은 두 번째부터 무시당한다★"""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 290_000)))
    ctx = _Ctx(brain=brain, home=tmp_path, extract=json.dumps([_row("Peach", 190_000)]))
    plugin.advise(ctx)
    assert ctx.notices, "★측정 무효★ 알림 자체가 안 떴습니다"

    core.remember_outcome(brain, "u1", "Flights ICN to Tokyo", "booked")
    plugin.advise(ctx)
    assert not ctx.notices and ctx.cleared


def test_the_notice_comes_down_once_the_plane_has_left(tmp_path):
    """★항공권에만 있는 끝이다★ 떠난 표가 싸졌다는 말은 값이 없다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    core.remember_search(brain, "u1", "ICN", "Tokyo",
                         _flights(_row("Peach", 290_000)), depart="2099-01-01")
    ctx = _Ctx(brain=brain, home=tmp_path,
               extract=json.dumps([_row("Peach", 190_000, depart="2099-01-01")]))
    plugin.advise(ctx)
    assert ctx.notices, "★측정 무효★ 알림 자체가 안 떴습니다"

    # 그 비행기가 떠난다 — 우리가 시각을 옮기는 대신 지난 날짜로 다시 남긴다
    node = next(iter(brain.find_entities("u1", kind="wish")))
    brain.update_entity("u1", node.id,
                        attrs={**node.attrs, "depart": "2020-01-01"})
    plugin.advise(ctx)
    assert not ctx.notices and ctx.cleared


def test_it_does_not_search_again_on_every_single_turn(tmp_path):
    """★`advise()`는 말이 오갈 때마다 불린다★ 매번 검색하면 대화 한 번에 웹 검색이
    지켜보는 수만큼 나간다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_search(brain, "u1", "ICN", "Tokyo", _flights(_row("Peach", 290_000)))
    plugin = FlightsPlugin()
    ctx = _Ctx(brain=brain, home=tmp_path, extract=json.dumps([_row("Peach", 190_000)]))
    plugin.advise(ctx)
    first = len(ctx.tool_calls)
    assert first, "★측정 무효★ 한 번도 안 찾아봤습니다"
    plugin.advise(ctx)
    assert len(ctx.tool_calls) == first, "말이 오갈 때마다 다시 검색하고 있습니다"


# ── ⑩ 화면 ───────────────────────────────────────────────────────────────────

def _screen(plugin, ctx):
    """★셸이 받는 그대로 본다★ 에이전트가 준 것을 그냥 읽으면 계약이 버리는 것을
    못 보고, 그러면 화면에 안 나오는 것을 나온다고 세게 된다."""
    return _normalize(plugin.view(ctx))


def test_an_empty_screen_still_says_something(tmp_path):
    blocks = _screen(FlightsPlugin(), _Ctx(home=tmp_path))["blocks"]
    assert blocks and blocks[0]["type"] == "text"


def test_the_screen_lines_the_flights_up_side_by_side(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    ctx = _Ctx(brain=brain, home=tmp_path)
    plugin.run(ctx, action="search", origin="ICN", destination="Tokyo")

    blocks = _screen(plugin, ctx)["blocks"]
    compare = next(b for b in blocks if b["type"] == "compare")
    names = [i["title"] for i in compare["items"]]
    assert "Peach" in names, f"★측정 무효★ 후보가 화면에 없습니다: {names}"
    # ★미는 것은 하나다★ 한 화면에 테두리가 둘이면 그것은 추천이 아니다
    assert sum(1 for i in compare["items"] if i["lead"]) == 1


def test_the_signals_reach_the_screen_as_words_not_numbers(tmp_path):
    """★분을 그대로 실으면 화면에 "515"가 뜬다★ 그 숫자를 읽을 수 있는 사람은 없다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    ctx = _Ctx(brain=brain, home=tmp_path, extract=json.dumps([
        _row("Peach", 210_000, stops=0, duration_minutes=155),
        _row("Korean Air", 380_000, stops=1, duration_minutes=515)]))
    plugin.run(ctx, action="search", origin="ICN", destination="Tokyo")

    compare = next(b for b in _screen(plugin, ctx)["blocks"] if b["type"] == "compare")
    signals = [i["signals"] for i in compare["items"]]
    assert signals[0]["stops"] == "Nonstop", signals
    assert signals[1]["duration"] == "8h 35m", signals
    # ★어휘의 주인은 화면 계약이다★ 우리 이름으로 칸을 늘리면 계약이 버린다
    assert set(compare["signals"]) <= set(_SIGNALS)


def test_the_cheapest_badge_is_decided_across_every_page(tmp_path):
    """★화면이 받은 한 쪽에서 고르면 다음 쪽에 더 싼 것이 있을 때 거짓말이 된다★"""
    rows = [_row(f"Air{n}", 300_000 + n) for n in range(8)]
    rows.append(_row("Bargain Air", 90_000))          # ★맨 뒤에 가장 싼 것★
    items = [{"price": f.price} for f in core.rank(core.to_flights(json.dumps(rows)))]
    assert core.cheapest_index(items) == 0            # 순위가 이미 앞으로 끌어 왔다

    # 그리고 정렬되지 않은 목록에서도 전체를 본다
    assert core.cheapest_index([{"price": 300}, {"price": 0}, {"price": 100}]) == 2
    assert core.cheapest_index([{"price": 0}, {}]) == -1


def test_the_screen_says_which_day_when_the_days_differ(tmp_path):
    """★같은 노선도 다른 날은 다른 것이다★ 날이 갈리는데 안 보이면 사용자는 넷을
    같은 날로 읽고, 그러면 값 비교가 통째로 뜻을 잃는다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    ctx = _Ctx(brain=brain, home=tmp_path, extract=json.dumps([
        _row("Peach", 210_000, depart="2026-09-10", stops=0),
        _row("Jeju Air", 240_000, depart="2026-09-11", stops=0)]))
    plugin.run(ctx, action="search", origin="ICN", destination="Tokyo")
    compare = next(b for b in _screen(plugin, ctx)["blocks"] if b["type"] == "compare")
    assert any("2026-09-10" in i["note"] for i in compare["items"])


def test_one_days_search_does_not_repeat_the_date_on_every_card(tmp_path):
    """★찍어 보고 알았다★ 카드 넷이 같은 날짜를 되풀이하면서 이유 문장을 카드 밖으로
    밀어냈다 — 그 날은 위 제목이 이미 말하고 있었다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    ctx = _Ctx(brain=brain, home=tmp_path, extract=json.dumps([
        _row("Peach", 210_000, depart="2026-09-10", stops=0, note="아침 출발"),
        _row("Jeju Air", 240_000, depart="2026-09-10", stops=0)]))
    plugin.run(ctx, action="search", origin="ICN", destination="Tokyo",
               depart="2026-09-10")
    screen = _screen(plugin, ctx)
    compare = next(b for b in screen["blocks"] if b["type"] == "compare")
    assert not any("2026-09-10" in i["note"] for i in compare["items"])
    # 그래도 그 날짜는 **화면 어딘가에** 있어야 한다 — 없으면 무슨 날 표인지 모른다
    group = next(b for b in screen["blocks"] if b["type"] == "group")
    assert "2026-09-10" in group["label"]


def test_the_screen_heading_is_not_the_memory_key(tmp_path):
    """★기억의 열쇠를 화면에 그대로 쓰지 않는다★ (한국어로 찍어 보고 알았다)

    노선 이름은 브레인에서 같은 노선을 하나로 모으는 열쇠라 **어느 언어에서도
    같아야 한다** — 옮기면 언어를 바꿀 때마다 같은 노선이 새로 생긴다. 그래서
    화면에는 어느 언어에서도 읽히는 줄을 따로 만든다.
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    ctx = _Ctx(brain=brain, home=tmp_path,
               extract=json.dumps([_row("Peach", 210_000, stops=0)]))
    plugin.run(ctx, action="search", origin="ICN", destination="Tokyo",
               depart="2026-09-10")
    screen = _screen(plugin, ctx)
    group = next(b for b in screen["blocks"] if b["type"] == "group")
    assert "ICN" in group["label"] and "Tokyo" in group["label"]
    assert "Flights" not in group["label"], "영어 문장이 화면 머리에 남았습니다"
    assert "2026-09-10" in group["label"]
    # ★그런데 기억의 열쇠는 그대로다★ 화면 줄과 열쇠를 같이 바꾸면 뜻이 없다
    assert core.recall_route(brain, "u1", "ICN", "Tokyo", "2026-09-10")["route"] \
        == "Flights ICN to Tokyo on 2026-09-10"


# ── 쪽 넘김 — ★말로도 손으로도 같은 문★ ──────────────────────────────────────

def test_saying_show_the_next_ones_moves_the_screen(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    rows = [_row(f"Air{n}", 100_000 + n * 1_000) for n in range(9)]
    ctx = _Ctx(brain=brain, home=tmp_path, extract=json.dumps(rows))
    plugin.run(ctx, action="search", origin="ICN", destination="Tokyo")

    first = next(b for b in _screen(plugin, ctx)["blocks"] if b["type"] == "compare")
    plugin.run(ctx, action="next")
    second = next(b for b in _screen(plugin, ctx)["blocks"] if b["type"] == "compare")
    assert [i["title"] for i in first["items"]] != [i["title"] for i in second["items"]]
    # ★2쪽에서 1위를 표시하면 화면에 없는 것을 가리키는 하이라이트가 된다★
    assert not any(i["lead"] for i in second["items"])

    plugin.run(ctx, action="prev")
    back = next(b for b in _screen(plugin, ctx)["blocks"] if b["type"] == "compare")
    assert [i["title"] for i in back["items"]] == [i["title"] for i in first["items"]]


def test_the_last_page_says_it_is_the_last(tmp_path):
    """★끝에서 첫 쪽으로 되감으면 사용자는 새 목록으로 읽는다★"""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    ctx = _Ctx(brain=brain, home=tmp_path,
               extract=json.dumps([_row("Peach", 210_000)]))
    plugin.run(ctx, action="search", origin="ICN", destination="Tokyo")
    assert "last page" in plugin.run(ctx, action="next")
    assert "first page" in plugin.run(ctx, action="prev")


def test_the_button_and_the_words_go_through_the_same_door(tmp_path):
    """★버튼에 "다음"이라 써 놓고 말로는 다른 낱말을 받으면 둘 중 하나를 못 쓴다★"""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = FlightsPlugin()
    rows = [_row(f"Air{n}", 100_000 + n) for n in range(9)]
    ctx = _Ctx(brain=brain, home=tmp_path, extract=json.dumps(rows))
    plugin.run(ctx, action="search", origin="ICN", destination="Tokyo")

    actions = next(b for b in _screen(plugin, ctx)["blocks"] if b["type"] == "actions")
    wanted = {a["args"].get("action") for a in actions["items"] if a.get("args")}
    assert "next" in wanted and "booked" in wanted
    assert wanted <= set(core.ACTIONS), f"화면이 없는 문을 부릅니다: {wanted}"

    # ★"끊었어"는 **어느 쪽에서나** 누를 수 있어야 한다★ (찍어 보고 알았다)
    # 그것은 항공편이 아니라 **노선**에 대한 표시라 3쪽에서 눌러도 뜻이 같다 —
    # 첫 쪽에만 두면 뒤쪽을 보다 결정한 사람은 답할 자리가 없어진다.
    plugin.run(ctx, action="next")
    later = next(b for b in _screen(plugin, ctx)["blocks"] if b["type"] == "actions")
    assert "booked" in {a["args"].get("action") for a in later["items"] if a.get("args")}


# ── 목적 (원칙 0 ①) ──────────────────────────────────────────────────────────

def test_the_agent_says_why_it_was_installed():
    """★`purpose`가 있어야 무엇을 남길지가 정해진다★(원칙 0 ①)"""
    assert len(FlightsPlugin.purpose.split()) > 20
    assert FlightsPlugin.purpose != FlightsPlugin.summary
