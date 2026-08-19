"""★고지된 것과 설치되는 것이 같은가★ — 마켓 에이전트가 재야 할 것.

저장소 안에 있을 때는 *"`features/`에 등록되는가"* 를 쟀다. 마켓으로 나온 지금은
등록을 코스모스의 로더가 **매니페스트를 읽어** 한다 — 그래서 재야 할 것이 바뀌었다.
★사용자가 승인한 것은 고지된 내용이다★ 코드가 그보다 넓으면 승인은 거짓이 된다.

이 파일이 지키는 것 넷:

  ① 진입점이 **실제 클래스**를 가리킨다(어긋나면 설치는 되는데 아무 일도 안 난다)
  ② 매니페스트의 역량이 코드와 **같다**(로더가 합집합으로 넓힌다)
  ③ 설치 화면이 **무엇을 기억하는지** 말한다 — 그것을 보고 승인한다
  ④ 문서가 **양식을 지킨다**(설치는 남의 코드를 내 기계에서 도는 일이다)
"""
from __future__ import annotations

import pathlib

from youtube_scout import YouTubePlugin

HERE = pathlib.Path(__file__).resolve().parent.parent


def _manifest() -> dict:
    import yaml
    return yaml.safe_load((HERE / "cosmos-agent.yaml").read_text(encoding="utf-8"))


def test_the_manifest_points_at_the_class_that_is_actually_here():
    """★진입점이 어긋나면 설치는 되는데 아무 일도 안 일어난다★"""
    import importlib
    module_name, _, class_name = _manifest()["entry"].partition(":")
    module = importlib.import_module(module_name)
    assert getattr(module, class_name, None) is YouTubePlugin


def test_the_manifest_declares_exactly_what_the_code_asks_for():
    """★로더는 **코드 ∪ 매니페스트**로 역량을 넓힌다★ 둘이 어긋나면 사용자가 승인한
    것과 집행되는 것이 갈린다 — 그리고 그 차이는 조용하다."""
    manifest = _manifest()
    assert sorted(manifest["capabilities"]) == sorted(YouTubePlugin.capabilities)
    assert manifest["tools"] == [YouTubePlugin.name]
    assert manifest["id"].endswith("/" + YouTubePlugin.name)
    assert manifest["version"] == YouTubePlugin.version


def test_the_manifest_asks_for_nothing_it_does_not_need():
    """★역량은 적을수록 좋다★ 안 쓰는 것을 받아 두면 사용자는 그만큼 더 넓게
    승인한 것이고, 그것은 우리가 쓰지도 않을 신뢰를 받아 챙긴 것이다."""
    assert not (_manifest().get("requires") or []), \
        "다른 에이전트가 필요 없는데 필요하다고 적었습니다"
    assert not _manifest()["requires_desktop"]


def test_publishing_is_disclosed_because_it_is_the_one_that_matters():
    """★남의 것을 읽는 역량과 **내 이름으로 내놓는** 역량은 다르다★

    설치 화면에서 사용자는 그 한 줄을 보고 승인한다 — 역량이 없으면 그 고지도 없다.
    """
    assert "media.publish" in _manifest()["capabilities"]
    assert "media.publish" in YouTubePlugin.capabilities


def test_the_agent_declares_what_it_will_know_about_you():
    """★무엇을 만들고 무엇을 보는지는 민감하다★ 설치 화면에서 사용자는 그것을 보고
    승인한다 — 역량이 없으면 그 고지도 없다."""
    from cosmos.core.capabilities import CAPABILITIES
    caps = YouTubePlugin.capabilities
    assert "memory" in caps and "network" in caps
    assert all(c in CAPABILITIES for c in caps), "표에 없는 역량은 끌 수 없다"


def test_the_readme_keeps_the_shape_the_market_asks_for():
    """★설치는 남의 코드를 내 기계에서 도는 일이다★ 무엇을 하는지 읽을 수 없으면
    승인할 근거도 없다. 특히 *"무엇을 **안** 하는가"* 에서 신뢰가 온다."""
    from cosmos.core.market import spec
    report = spec.check_readme((HERE / "README.md").read_text(encoding="utf-8"))
    assert report["ok"], report


def test_the_install_screen_says_what_it_will_remember():
    """★설치 화면은 코드를 받기 **전에** 그려진다★ 무엇을 기억하는지가 거기 없으면
    사용자는 설치한 뒤에야 그것을 알게 된다."""
    blurb = _manifest()["description"].lower()
    assert "keep" in blurb or "remember" in blurb
    assert YouTubePlugin.brain["stores"] and YouTubePlugin.brain["reads"]
    assert YouTubePlugin.brain.get("settled"), \
        "안 남기기로 한 것도 적어야 한다 — 뭉개면 고칠 것이 '검토됨'으로 묻힌다"


def test_choosing_not_to_speak_first_is_written_down():
    """★"검토했고 **안 하기로** 했다"는 **닫힌 것**이다★ (Sean 결정 2026-08-19)

    비워 두면 *"아직 안 봤다"* 와 구별되지 않아, 다음 사람이 **이미 정한 것을 다시
    정한다**(`brain`의 `gap`/`settled`를 가른 것과 정확히 같은 이유).

    ⚠️ 그리고 ★근거가 있어야 한다★ — `settled`가 빈 문자열이면 그것은 결정이 아니라
    빈칸이다.
    """
    assert not YouTubePlugin.makes_offers and not YouTubePlugin.raises_notices, \
        "먼저 안 걸기로 해 놓고 훅을 켜 두었습니다"
    why = str((getattr(YouTubePlugin, "collab", None) or {}).get("settled") or "")
    assert len(why.split()) > 20, f"안 하기로 한 근거가 없습니다: {why!r}"
    # ★선언은 영어다★ 마켓은 남이 만든 것을 받는 곳이다
    assert not any("가" <= ch <= "힣" for ch in why), "선언 문구가 한국어입니다"
