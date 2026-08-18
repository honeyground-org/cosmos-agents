"""쇼핑 에이전트(Phase S) — **말로 시키면 찾고, 화면이 비교한다**.

이 파일이 지키는 것 다섯:

  ① 에이전트가 **실제로 등록된다** — 안 되면 말로 시킬 수 없다
  ② ★못 찾았으면 **그렇다고 말한다**★ 빈 결과에 그럴듯한 말을 붙이면 사용자는
     "그런 물건이 없다"로 읽는다
  ③ ★**말은 짧다**★ 목록을 읽어 주면 사람은 넷째쯤에서 앞을 잊는다 — 비교는 화면이
  ④ **도구와 화면이 같은 것을 본다** — 화면이 다시 검색하면 두 번 돈다
  ⑤ ★**지난번 이야기가 맨 위**★ 이것이 이 에이전트의 값어치다
"""
from __future__ import annotations

import json

import pytest

from shopping_scout import ShoppingPlugin, _headlines, _to_candidate
import shopping_core as shopping
from cosmos.runtime.memory_lite.provider import LiteMemoryProvider


class _Ctx:
    """ToolContext 대역 — 에이전트가 실제로 쓰는 표면만."""

    def __init__(self, tmp_path, brain=None, *, search="", extract="[]"):
        self._dir = tmp_path
        self.brain = brain
        self.user_id = "u1"
        self._search = search
        self._extract = extract
        self.logs: list[str] = []
        self.tool_calls: list[tuple] = []

    def write_log(self, message, speaker=None, level="info"):
        self.logs.append(message)

    def run_tool(self, name, args):
        self.tool_calls.append((name, args))
        return self._search

    def think(self, prompt, *, system=None, fast=False):
        return self._extract

    def data_dir(self, component):
        path = self._dir / "agentdata" / component
        path.mkdir(parents=True, exist_ok=True)
        return path


_ROWS = json.dumps([
    {"title": "소니 WF-1000XM5", "price": 289000, "seller": "소니스토어",
     "url": "https://example.com/a", "signals": {"rating": 4.6, "review_count": 812},
     "note": "노이즈 캔슬링이 가장 좋다는 평"},
    {"title": "젠하이저 모멘텀 4", "price": 254000, "seller": "하이파이샵",
     "url": "https://example.com/b", "signals": {"rating": 4.4}},
    {"title": "에어팟 프로 2", "price": 299000, "signals": {"rating": 4.5}},
], ensure_ascii=False)


# ── ① 매니페스트와 코드가 **같은 말을 한다** ────────────────────────────────
#
# 예전에는 여기서 *"`features/`에 등록되는가"* 를 쟀다. 마켓으로 나온 지금은 등록을
# 코스모스의 로더가 **매니페스트를 읽어** 한다 — 그래서 재야 할 것이 바뀌었다:
# ★고지된 것과 설치되는 것이 같은가★. 사용자가 승인한 것은 고지된 내용이다.

def _manifest() -> dict:
    import yaml
    from pathlib import Path
    here = Path(__file__).resolve().parent.parent
    return yaml.safe_load((here / "cosmos-agent.yaml").read_text(encoding="utf-8"))


def test_the_manifest_points_at_the_class_that_is_actually_here():
    """★진입점이 어긋나면 설치는 되는데 아무 일도 안 일어난다★"""
    import importlib
    module_name, _, class_name = _manifest()["entry"].partition(":")
    module = importlib.import_module(module_name)
    assert getattr(module, class_name, None) is ShoppingPlugin


def test_the_manifest_declares_exactly_what_the_code_asks_for():
    """★로더는 **코드 ∪ 매니페스트**로 역량을 넓힌다★ 둘이 어긋나면 사용자가 승인한
    것과 집행되는 것이 갈린다 — 그리고 그 차이는 조용하다."""
    manifest = _manifest()
    assert sorted(manifest["capabilities"]) == sorted(ShoppingPlugin.capabilities)
    assert manifest["tools"] == [ShoppingPlugin.name]
    assert manifest["id"].endswith("/" + ShoppingPlugin.name)


def test_the_manifest_says_it_needs_wallet():
    """★"결제 도와줘"를 눌렀는데 조용한 것이 가장 나쁘다★ 월렛 없이도 비교까지는
    되지만, 그 사실을 설치 화면이 말해야 한다."""
    assert "wallet" in (_manifest().get("requires") or [])


def test_the_agent_declares_what_it_will_know_about_you():
    """★쇼핑 이력은 매우 민감하다★ 설치 화면에서 사용자는 "이 에이전트가 내가 뭘
    사려는지 알게 된다"를 보고 승인한다 — 역량이 없으면 그 고지도 없다."""
    from cosmos.core.capabilities import CAPABILITIES
    caps = ShoppingPlugin.capabilities
    assert "shopping.search" in caps and "memory" in caps
    assert all(c in CAPABILITIES for c in caps), "표에 없는 역량은 끌 수 없다"


# ── ② 못 찾았으면 그렇다고 말한다 ───────────────────────────────────────────

def test_nothing_found_is_said_plainly(tmp_path):
    ctx = _Ctx(tmp_path, search="", extract="[]")
    out = ShoppingPlugin().run(ctx, query="무선 이어폰")
    # ★번역문이 아니라 **영어 원문**을 본다★ 검사 언어(`COSMOS_LANG=en`)가 원문을
    # 정하므로, 번역문을 검사하면 언어를 바꿀 때마다 이 그물이 조용히 눈이 먼다.
    assert "could not find" in out.lower(), f"빈 결과에 그럴듯한 말을 붙였다: {out}"


def test_a_broken_search_does_not_pretend(tmp_path):
    class _Boom(_Ctx):
        def run_tool(self, name, args):
            raise RuntimeError("검색이 죽었다")

    out = _Boom(tmp_path) and ShoppingPlugin().run(_Boom(tmp_path), query="이어폰")
    assert "could not find" in out.lower()


def test_a_model_that_returns_garbage_does_not_crash_the_agent(tmp_path):
    ctx = _Ctx(tmp_path, search="결과 있음", extract="이건 JSON이 아닙니다")
    assert "could not find" in ShoppingPlugin().run(ctx, query="이어폰").lower()


def test_an_invented_price_is_not_accepted():
    """★모델이 지어낸 숫자는 화면에서 사실이 된다★"""
    assert _to_candidate({"title": "A", "price": "비쌈"}).price == 0
    assert _to_candidate({"title": "A", "signals": {"made_up": 1}}).signals == {}
    assert _to_candidate({"title": ""}) is None


def test_the_time_a_price_was_read_comes_from_us_not_the_model(tmp_path):
    """모델이 준 시각을 믿으면 **지어낸 값**이 "언제 잰 것"으로 들어간다."""
    got = _to_candidate({"title": "A", "price": 1000, "seen_at": "1999-01-01T00:00:00"})
    assert got.seen_at and not got.seen_at.startswith("1999")


# ── ③ 말은 짧다 ────────────────────────────────────────────────────────────

def test_the_spoken_answer_stays_short(tmp_path):
    """★목록을 읽어 주면 사람은 넷째쯤에서 앞을 잊는다★ 비교는 화면이 한다."""
    ctx = _Ctx(tmp_path, search="결과", extract=_ROWS)
    out = ShoppingPlugin().run(ctx, query="무선 이어폰")
    named = [line for line in out.splitlines() if "원" in line]
    assert len(named) <= 2, f"말이 너무 길다({len(named)}개를 읽는다): {out}"
    assert "on the screen" in out.lower(), "나머지가 화면에 있다는 것을 말하지 않는다"


# ── ④ 도구와 화면이 같은 것을 본다 ──────────────────────────────────────────

def test_the_screen_reads_what_the_tool_already_found(tmp_path):
    """★화면이 다시 검색하면 두 번 돈다★ — 느리고, 두 번째 결과가 다르면 말과
    화면이 서로 다른 것을 말한다."""
    ctx = _Ctx(tmp_path, search="결과", extract=_ROWS)
    agent = ShoppingPlugin()
    agent.run(ctx, query="무선 이어폰")

    before = len(ctx.tool_calls)
    view = agent.view(ctx)
    assert len(ctx.tool_calls) == before, "화면이 검색을 다시 돌렸다"

    # ★블록 **이름**이 아니라 **후보가 화면에 닿았는가**를 잰다★(21차 교훈)
    # 예전에는 `"compare" in kinds`로 박혀 있었다. AS-6에서 같은 비교를 `html`
    # 문서로 그리게 바뀌자 이 그물이 *"뷰의 핵심이 빠졌다"* 로 울었는데, 화면에는
    # 오히려 더 많은 것이 그려지고 있었다 — 재는 것이 도달 가능성이 아니었다.
    drawn = json.dumps(view["blocks"], ensure_ascii=False)
    # ★한 화면에 오는 것은 **첫 쪽**이다★ (2026-08-18) 나머지는 버려진 것이 아니라
    # *"다음 보기"* 뒤에 있다 — 그것은 아래의 쪽 넘김 그물이 따로 잰다.
    for row in json.loads(_ROWS)[:shopping.PAGE_SIZE]:
        assert row["title"] in drawn, f"후보 '{row['title']}'가 화면에 안 실렸다"


def test_an_empty_screen_says_what_to_do(tmp_path):
    """★빈 화면은 고장으로 읽힌다★(M-H20)"""
    view = ShoppingPlugin().view(_Ctx(tmp_path))
    assert view["blocks"] and view["blocks"][0]["type"] == "text"


# ── ⑤ 지난번 이야기가 맨 위 ─────────────────────────────────────────────────

def test_a_price_drop_leads_the_screen(tmp_path):
    """★이것이 이 에이전트의 값어치다★"""
    diff = {"first_time": False, "stale": False,
            "changes": [{"title": "소니 WF-1000XM5", "delta": -12000,
                         "direction": "down", "before": 289000, "after": 277000}],
            "gone": [], "new": []}
    lines = _headlines(diff)
    assert lines and "12,000" in lines[0]["text"] \
        and "went down" in lines[0]["text"].lower()
    assert lines[0]["tone"] == "good"


def test_the_first_time_says_nothing_about_last_time():
    assert _headlines({"first_time": True}) == []


def test_a_very_old_search_is_not_brought_up():
    """반 년 전 것을 들이밀면 도움이 아니라 참견이다."""
    assert _headlines({"first_time": False, "stale": True,
                       "changes": [{"title": "A", "delta": -1000,
                                    "direction": "down"}]}) == []


def test_the_second_run_knows_the_first(tmp_path):
    """★끝까지 이어지는가★ 한 번 찾고, 값이 내리고, 다시 물으면 **그것을 말한다**."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    agent = ShoppingPlugin()

    first = _Ctx(tmp_path, brain=brain, search="결과", extract=_ROWS)
    agent.run(first, query="무선 이어폰")

    cheaper = json.dumps([{"title": "소니 WF-1000XM5", "price": 259000,
                           "signals": {"rating": 4.6}}], ensure_ascii=False)
    second = _Ctx(tmp_path, brain=brain, search="결과", extract=cheaper)
    out = agent.run(second, query="무선 이어폰")
    assert "went down" in out.lower(), f"지난번을 언급하지 않는다: {out}"


# ── ⑥ ★"다음 보기" — 넷이 전부가 아니다★ (Sean 요구 2026-08-18) ──────────────
#
# ⚠️ ★순수 함수만 재면 배선이 끊겨도 초록이다★(30차 교훈) `page_of`가 잘 도는지는
# `test_shopping.py`가 재고, 여기서는 **화면과 도구가 그것을 실제로 쓰는가**를 잰다.

_MANY = json.dumps([{"title": f"후보 {n:02d}", "price": 10_000 + n,
                     "url": f"https://example.com/{n}",
                     "signals": {"rating": 4.0}} for n in range(10)],
                   ensure_ascii=False)


def _open_a_long_list(tmp_path):
    agent = ShoppingPlugin()
    ctx = _Ctx(tmp_path, search="결과", extract=_MANY)
    agent.run(ctx, query="이어폰")
    return agent, ctx


def _titles_on_screen(agent, ctx) -> str:
    return json.dumps(agent.view(ctx)["blocks"], ensure_ascii=False)


def test_the_screen_shows_one_page_not_the_whole_list(tmp_path):
    """★스크롤해야 비교가 되면 "한눈에 결정"이 깨진다★ 화면에 오는 것은 첫 쪽뿐이다."""
    agent, ctx = _open_a_long_list(tmp_path)
    drawn = _titles_on_screen(agent, ctx)
    assert "후보 00" in drawn and "후보 03" in drawn
    assert "후보 04" not in drawn, "한 화면에 다섯째가 실렸다 — 쪽이 안 나뉜다"


def test_saying_show_the_next_ones_moves_the_screen(tmp_path):
    """★말한 것이 **화면을 바꿔야** 한다★ 도구만 답하고 화면이 그대로면 안 넘어간 것이다."""
    agent, ctx = _open_a_long_list(tmp_path)
    agent.run(ctx, action="next")
    drawn = _titles_on_screen(agent, ctx)
    assert "후보 04" in drawn and "후보 07" in drawn
    assert "후보 00" not in drawn, "다음 쪽인데 첫 쪽이 그대로 있다"


def test_going_back_returns_to_the_first_page(tmp_path):
    agent, ctx = _open_a_long_list(tmp_path)
    agent.run(ctx, action="next")
    agent.run(ctx, action="prev")
    assert "후보 00" in _titles_on_screen(agent, ctx)


def test_the_end_of_the_list_says_so_instead_of_wrapping(tmp_path):
    """★끝에서 첫 쪽으로 되감으면 사용자는 그것을 **새 목록**으로 읽는다★"""
    agent, ctx = _open_a_long_list(tmp_path)
    agent.run(ctx, action="next")           # 2쪽 (04~07)
    agent.run(ctx, action="next")           # 3쪽 (08~09) — 마지막
    out = agent.run(ctx, action="next")
    assert "last" in out.lower(), f"끝이라고 말하지 않는다: {out}"
    assert "후보 08" in _titles_on_screen(agent, ctx), "끝에서 첫 쪽으로 되감겼다"


def test_a_new_search_starts_from_the_first_page(tmp_path):
    """★3쪽을 보던 중에 다른 것을 찾으면 새 목록의 9번째부터 보인다★ — 고장으로 읽힌다."""
    agent, ctx = _open_a_long_list(tmp_path)
    agent.run(ctx, action="next")
    agent.run(ctx, query="키보드")
    assert "후보 00" in _titles_on_screen(agent, ctx)


def test_the_button_number_points_at_the_whole_list_not_the_page(tmp_path):
    """★결제 대상이 미끄러지는 것은 가장 나쁜 종류의 사고다★

    쪽마다 1번부터 세면 3쪽의 1번을 누를 때 1쪽의 1번이 결제된다.
    """
    agent, ctx = _open_a_long_list(tmp_path)
    agent.run(ctx, action="next")
    card = next(b for b in agent.view(ctx)["blocks"] if b["type"] == "compare")["items"][0]
    assert card["title"] == "후보 04"
    assert card["action"]["args"]["index"] == 5, "쪽마다 1번부터 세고 있다"


def test_there_is_nothing_to_turn_when_no_list_is_open(tmp_path):
    """빈 상태에서 "다음"이라고 하면 **그렇다고 말한다**(조용히 아무 일도 없으면 고장이다)."""
    out = ShoppingPlugin().run(_Ctx(tmp_path), action="next")
    assert "no list" in out.lower()


def test_the_spoken_answer_offers_the_next_page(tmp_path):
    """★더 있다는 것을 말해 줘야 넘긴다★ 단추만 두면 말로 쓰는 사람은 모른다."""
    agent = ShoppingPlugin()
    said = agent.run(_Ctx(tmp_path, search="결과", extract=_MANY), query="이어폰")
    assert "next" in said.lower(), f"다음 쪽이 있다는 말이 없다: {said}"


def test_cheapest_means_cheapest_of_all_not_of_this_page(tmp_path):
    """★한 쪽만 보고 "가장 싸다"고 쓰면 **거짓말**이 된다★ (2026-08-18 · 2쪽을 찍고 알았다)

    예전에는 화면이 **받은 넷** 중 가장 싼 것에 표를 달았다. 다음 쪽에 더 싼 것이
    있으면 두 쪽에 최저가가 하나씩 생겼고, 둘 다 "가장 싸다"고 말했다.
    """
    # ★평점이 다 같으면 순위가 **값순**이 되어 최저가가 저절로 1위다★ — 그러면 이
    # 그물은 아무것도 안 재게 된다. 평점을 내리면서 값도 내려야 둘이 갈린다.
    rows = json.dumps([{"title": f"후보 {n:02d}", "price": 20_000 - n * 500,
                        "url": f"https://example.com/{n}",
                        "signals": {"rating": round(4.9 - n * 0.1, 1)}}
                       for n in range(10)], ensure_ascii=False)
    agent = ShoppingPlugin()
    ctx = _Ctx(tmp_path, search="결과", extract=rows)
    agent.run(ctx, query="이어폰")

    def marks(view):
        return [i["mark"] for b in view["blocks"] if b["type"] == "compare"
                for i in b["items"] if i["mark"]]

    first = marks(agent.view(ctx))
    assert any("Best" in m for m in first), "1쪽에 추천 표시가 없다"
    assert not any("Cheapest" in m for m in first), \
        "★가장 싼 것은 3쪽에 있는데 1쪽에 최저가를 달았다★"
    agent.run(ctx, action="next")
    agent.run(ctx, action="next")
    assert any("Cheapest" in m for m in marks(agent.view(ctx))), \
        "정작 진짜 최저가가 있는 쪽에는 표시가 없다"


def test_only_the_pick_is_outlined(tmp_path):
    """★테두리는 **하나**다★ 둘이 두드러지면 어느 쪽을 고르라는 것인지 알 수 없다."""
    agent, ctx = _open_a_long_list(tmp_path)
    cards = next(b for b in agent.view(ctx)["blocks"] if b["type"] == "compare")["items"]
    assert sum(1 for c in cards if c["lead"]) == 1
