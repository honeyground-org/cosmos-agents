"""유튜브 에이전트(Phase MA ①) — 찾고, 보고, ★올린다★.

이 파일이 지키는 것 여섯:

  ① ★**공개는 되돌릴 수 없다**★ 모르는 낱말은 `private`으로 떨어지고, 요청과
     달라졌으면 **그 사실을 말한다**. 조용히 좁히면 "왜 안 보이지"가 되고,
     조용히 넓히면 남의 영상이 세상에 나간다
  ② ★열쇠가 없으면 **무엇이 없는지 이름으로** 말한다★ 'not configured'는
     사용자에게 아무것도 알려 주지 않는다(함정 44)
  ③ 스쳐 본 것과 **지목해서 본 것**을 가른다 — 검색 목록을 통째로 남기면
     브레인이 보지도 않은 영상으로 채워진다
  ④ ★조회수는 기억하지 않는다★ 그 순간의 수치라 남기는 순간 거짓이 된다
  ⑤ 주소는 **파싱한다** — `evil.example/youtube.com/...`을 유튜브로 읽으면 안 된다
  ⑥ 업로드는 실제 배선(토큰 → 자리 잡기 → 파일 밀기)을 지나간다

★판정이 순수 함수라서 검사가 가능하다★(29차 교훈) — 네트워크 안에 묻어 두었다면
낱말만 남기고 동작을 뒤집는 뮤테이션이 그대로 빠져나갔을 것이다.
"""
from __future__ import annotations

import json

import pytest

from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
import youtube_scout as core
from youtube_scout import YouTubePlugin


class _Ctx:
    """ToolContext 대역 — 에이전트가 실제로 쓰는 표면만."""

    def __init__(self, tmp_path, brain=None, *, thought="a summary"):
        self._dir = tmp_path
        self.brain = brain
        self.user_id = "u1"
        self.logs: list[str] = []
        self.tool_calls: list[tuple] = []
        self._thought = thought

    def write_log(self, message, speaker=None, level="info"):
        self.logs.append(message)

    def run_tool(self, name, args):
        self.tool_calls.append((name, args))
        return f"Opened {args.get('url', '')}"

    def think(self, prompt, *, system=None, fast=False):
        return self._thought

    def data_dir(self, component):
        path = self._dir / "agentdata" / component
        path.mkdir(parents=True, exist_ok=True)
        return path


@pytest.fixture
def keys(monkeypatch):
    """금고에 열쇠가 들어 있는 상태. ★`credentials` 층에서 가로챈다★ —
    `agent_settings.reveal`을 가로채면 **에이전트 이름을 맞게 넘기는지**가
    검사 밖으로 나간다(대역은 가장 낮은 층에)."""
    from cosmos.core import credentials
    store = {("youtube", "api_key"): "KEY",
             ("youtube", "client_id"): "CID",
             ("youtube", "client_secret"): "CSECRET",
             ("youtube", "refresh_token"): "RTOKEN"}
    asked: list[tuple] = []

    def _reveal(agent, field, *, user_id=""):
        asked.append((agent, field))
        return store.get((agent, field))

    monkeypatch.setattr(credentials, "reveal", _reveal)
    return asked


# ── ① 공개 범위 — fail-closed ────────────────────────────────────────────────

@pytest.mark.parametrize("asked,default,expected", [
    ("public", "", "public"),               # 정확히 말하면 그대로
    ("unlisted", "", "unlisted"),
    ("", "unlisted", "unlisted"),           # 안 말하면 사용자가 정한 기본값
    ("", "", "private"),                    # 아무것도 없으면 가장 좁게
    ("PUBLIC", "", "public"),               # 대소문자는 같은 말이다
    ("everyone", "", "private"),            # ★모르는 낱말은 좁은 쪽으로★
    ("public!", "", "private"),
    ("", "world", "private"),               # 기본값이 이상해도 넓어지지 않는다
])
def test_privacy_never_widens_by_accident(asked, default, expected):
    assert core.privacy_of(asked, default) == expected


def test_the_safe_privacy_is_the_narrowest_one_in_the_table():
    """★표의 순서가 곧 안전 순서다★ 누가 순서를 바꾸면 이 검사가 운다."""
    assert core.SAFE_PRIVACY == "private"
    assert core.PRIVACY[0] == core.SAFE_PRIVACY
    assert set(core.PRIVACY) == {"private", "unlisted", "public"}


def test_a_privacy_we_did_not_recognise_is_reported_not_swallowed(tmp_path):
    """모르는 낱말로 청했으면 **좁혔다고 말한다** — 조용하면 사용자는 공개된 줄 안다."""
    plan = core.plan_upload("/x/v.mp4", privacy="everyone", exists=lambda p: True)
    assert plan.privacy == "private" and plan.narrowed is True
    exact = core.plan_upload("/x/v.mp4", privacy="public", exists=lambda p: True)
    assert exact.privacy == "public" and exact.narrowed is False
    silent = core.plan_upload("/x/v.mp4", exists=lambda p: True)
    assert silent.privacy == "private" and silent.narrowed is False


# ── ② 열쇠가 없으면 무엇이 없는지 말한다 ──────────────────────────────────────

def test_missing_keys_are_named_one_by_one():
    assert core.missing_for("search", {}) == ("api_key", "google")
    assert core.missing_for("search", {"api_key": "K"}) == ()
    # ★올리는 데 필요한 것이 **하나**로 줄었다★(Phase OA) — 예전에는 셋이었고,
    # 사용자가 구글 클라우드에서 복사해 와야 했다
    assert core.missing_for("upload", {}) == ("google",)
    assert core.missing_for("upload", {"google": "connected"}) == ()
    # 빈 문자열은 "있다"가 아니다 — 저장은 됐지만 값이 없는 칸이 실제로 생긴다
    assert core.missing_for("search", {"api_key": "  "}) == ("api_key", "google")


def test_reading_takes_either_the_button_or_a_key(tmp_path):
    """★원클릭★(Sean 요구 2026-08-19) 읽기는 API 키로도 되고 구글 연결로도 된다.

    ⚠️ 이 둘을 `needs`에 나란히 적으면 *"둘 다 있어야 한다"* 가 되어, ★버튼을 누른
    사람이 키까지 넣어야★ 한다. 뜻이 다른 두 관계를 한 칸에 뭉치면 한쪽이 틀린다.
    """
    for action in ("search", "info", "summarize", "trending"):
        assert core.missing_for(action, {"google": "connected"}) == (), \
            f"{action}: 버튼을 눌렀는데도 막습니다"
        assert core.missing_for(action, {"api_key": "K"}) == (), \
            f"{action}: 자기 키를 넣었는데도 막습니다"
        assert core.missing_for(action, {}) != ()


def test_one_allow_screen_covers_reading_and_uploading():
    """★허용 화면을 두 번 띄우지 않는다★ 예전에는 `upload` 범위만 요청해서,
    올릴 수는 있는데 **찾을 수는 없는** 상태가 됐다."""
    spec = next(s for s in YouTubePlugin.settings if s["id"] == "google")
    joined = " ".join(spec["scopes"])
    assert "youtube.readonly" in joined and "youtube.upload" in joined


def test_play_needs_no_key_at_all():
    """★열쇠가 없어도 되는 일이 있어야 한다★ 전부 막으면 이 에이전트는
    키를 안 넣은 사람에게 **아무것도 못 하는 물건**으로 보인다."""
    assert core.ACTIONS["play"]["needs"] == ()
    assert not core.ACTIONS["play"].get("needs_any")
    assert core.missing_for("play", {}) == ()
    assert core.missing_for("play", {}) == ()


def test_without_a_key_the_answer_says_which_key_and_where(tmp_path, monkeypatch):
    from cosmos.core import credentials
    monkeypatch.setattr(credentials, "reveal", lambda *a, **k: None)
    answer = YouTubePlugin().run(_Ctx(tmp_path), action="search", query="cats")
    assert "settings" in answer.lower()
    # ★고장처럼 들리면 안 된다★ 무엇을 하면 되는지가 답에 있어야 한다.
    # ★그리고 그 "무엇"이 **버튼**이어야 한다★(Sean 요구 2026-08-19) — 예전에는
    # 이 자리가 *"구글 클라우드 콘솔에서 키를 만들어 오세요"* 였고, 개발자가
    # 아니면 거기서 멈췄다(실측: 브레인에 남은 것 0건).
    assert "Connect" in answer or "not switched on" in answer
    assert "Google Cloud Console" not in answer, \
        "아직도 사용자를 구글 클라우드로 보내고 있습니다"


def test_upload_without_a_connection_says_whose_job_it_is(tmp_path, monkeypatch):
    """★할 일이 **누구에게** 있는지 가른다★(Phase OA · Sean: 쉽게 쓸 수 있게)

    예전에는 *"client_id, client_secret, refresh_token이 없다"* 였고, 그것은
    사용자에게 **구글 클라우드에 가서 앱을 만들라**는 뜻이었다 — 개발자가 아니면
    거기서 멈춘다. 우리가 등록하지 않아서 안 되는 것이면 **그렇게** 말해야 한다.
    """
    from cosmos.core import appauth, credentials
    monkeypatch.setattr(credentials, "reveal",
                        lambda agent, field, **k: "KEY" if field == "api_key" else None)

    # ① 우리 등록이 아직 없다 → 우리 할 일이라고 말한다
    monkeypatch.setitem(appauth.PROVIDERS["google"], "client_id", "")
    answer = YouTubePlugin().run(_Ctx(tmp_path), action="upload", file="/x/v.mp4")
    assert "ours to do, not yours" in answer
    assert "console.cloud.google.com" not in answer, \
        "★사용자를 구글 클라우드로 보내고 있습니다★ 그것이 없애려던 화면입니다"

    # ② 등록이 되어 있다 → 할 일은 **버튼 하나**다
    monkeypatch.setitem(appauth.PROVIDERS["google"], "client_id", "our-app.apps.example")
    answer = YouTubePlugin().run(_Ctx(tmp_path), action="upload", file="/x/v.mp4")
    assert "press Connect" in answer and "one click" in answer
    assert "never see your password" in answer


def test_someone_who_pasted_the_old_keys_still_works(tmp_path, monkeypatch):
    """★새 길이 생겼다고 옛 길을 끊지 않는다★ 이미 넣어 둔 사람이 갑자기 못 쓰게
    되면 그것은 개선이 아니라 고장이다."""
    from cosmos.core import credentials
    old = {"api_key": "KEY", "client_id": "CID", "client_secret": "CS",
           "refresh_token": "RT"}
    monkeypatch.setattr(credentials, "reveal",
                        lambda agent, field, **k: old.get(field))
    plugin = YouTubePlugin()
    # 옛 세 칸이 다 있으면 **연결된 것으로 친다**
    assert core.missing_for("upload", plugin._have(_Ctx(tmp_path))) == ()


def test_one_missing_old_key_is_not_enough(tmp_path, monkeypatch):
    """세 칸 중 하나라도 비면 옛 길로도 못 간다 — 반쯤 채운 것을 됐다고 하면
    실패는 저장할 때가 아니라 올릴 때 드러난다."""
    from cosmos.core import credentials
    half = {"api_key": "KEY", "client_id": "CID", "client_secret": "CS"}
    monkeypatch.setattr(credentials, "reveal",
                        lambda agent, field, **k: half.get(field))
    plugin = YouTubePlugin()
    assert core.missing_for("upload", plugin._have(_Ctx(tmp_path))) == ("google",)


# ── ⑤ 주소는 파싱한다 ────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("youtube.com/watch?v=dQw4w9WgXcQ&t=30", "dQw4w9WgXcQ"),
    ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    # ★가짜 호스트★ — 문자열로 잘랐다면 여기서 통과했을 것이다
    ("https://evil.example/youtube.com/watch?v=dQw4w9WgXcQ", ""),
    ("https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ", ""),
    ("just some words", ""),
    ("", ""),
    ("tooshort", ""),
])
def test_a_video_reference_is_parsed_not_pattern_matched(text, expected):
    assert core.video_ref(text) == expected


# ── 정규화 ───────────────────────────────────────────────────────────────────

def test_both_shapes_of_the_api_answer_become_one_shape():
    """검색은 `{"id": {"videoId": …}}`, 조회는 `{"id": "…"}` — 부르는 쪽이
    가르면 그 분기가 언젠가 한쪽만 고쳐진다."""
    search = core.normalize({"items": [
        {"id": {"videoId": "aaaaaaaaaaa"},
         "snippet": {"title": "A", "channelTitle": "C", "channelId": "UC1"}}]})
    listed = core.normalize({"items": [
        {"id": "aaaaaaaaaaa", "snippet": {"title": "A", "channelTitle": "C"},
         "statistics": {"viewCount": "1234"}}]})
    assert [v.video_id for v in search] == [v.video_id for v in listed] == ["aaaaaaaaaaa"]
    assert listed[0].views == 1234 and search[0].views == 0
    assert listed[0].url == "https://www.youtube.com/watch?v=aaaaaaaaaaa"


def test_a_broken_answer_does_not_take_the_agent_down():
    assert core.normalize({}) == []
    assert core.normalize({"items": [{"snippet": {"title": "no id"}}, "junk"]}) == []
    assert core.normalize(None) == []


def test_the_list_is_capped():
    payload = {"items": [{"id": f"id{i:09d}", "snippet": {}} for i in range(50)]}
    assert len(core.normalize(payload)) == core.MAX_RESULTS


# ── ③④ 브레인 — 지목한 것만, 순간값은 빼고 ──────────────────────────────────

def test_a_video_you_looked_up_leaves_its_channel_not_its_title(tmp_path):
    """★영상 제목은 그래프 노드가 되지 않는다★ (Sean 결정 2026-08-19 · 실측)

    착수 전 실측: `topic` 노드 116개 중 ★64개(55%)가 페이지 제목 모양★이었고
    (`고민은 배송만 늦출 뿐.. 나의 첫 맥북 | MacBook Air... - YouTube`) 출처는
    `tool.web_search.v1` 95개였다. 옛 설계대로 켜면 **같은 오염을 더 붓는다**.

    ★대신 채널이 선다★ 채널 이름은 짧고, 반복되고, 지속된다.
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    video = core.Video(video_id="aaaaaaaaaaa", title="How tides work",
                       channel="Sea School", channel_id="UC9", views=98765)
    channel_id = core.remember_video(brain, "u1", video)
    assert channel_id

    assert brain.find_entities("u1", kind="topic") == [], \
        "영상 제목이 다시 그래프 노드가 되고 있습니다"
    orgs = {e.name: e for e in brain.find_entities("u1", kind="org")}
    assert "Sea School" in orgs
    assert orgs["Sea School"].attrs["youtube_channel_id"] == "UC9"
    # ★조회수는 남지 않는다★ 남기면 곧 거짓이 된다
    assert "views" not in orgs["Sea School"].attrs

    # ★본 사실 자체는 **기억 항목**으로 남는다★ — 그래야 낱말로 닿고, 반복을 센다
    kept = brain.recent("u1", k=10, kinds=[core.ITEM_KIND])
    assert len(kept) == 1 and "How tides work" in kept[0].text
    assert kept[0].meta["video_id"] == "aaaaaaaaaaa"
    assert "views" not in kept[0].meta


def test_a_video_with_no_channel_still_leaves_the_memory(tmp_path):
    """★채널을 모른다고 본 사실까지 버리지 않는다★ — 그러면 되읽을 것이 없어진다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    assert core.remember_video(brain, "u1",
                               core.Video(video_id="b" * 11, title="No channel")) == ""
    assert len(brain.recent("u1", k=10, kinds=[core.ITEM_KIND])) == 1


def test_the_search_list_is_not_remembered_but_a_lookup_is(tmp_path, keys, monkeypatch):
    """★이 검사가 이 에이전트의 원칙 0 ①이다★ — 스쳐 본 것은 안 남는다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    ctx = _Ctx(tmp_path, brain=brain)
    plugin = YouTubePlugin()
    payload = {"items": [{"id": {"videoId": "aaaaaaaaaaa"},
                          "snippet": {"title": "Result one", "channelTitle": "Ch"}},
                         {"id": {"videoId": "bbbbbbbbbbb"},
                          "snippet": {"title": "Result two", "channelTitle": "Ch"}}]}
    monkeypatch.setattr(plugin, "_api", lambda ctx, path, params: payload)

    plugin.run(ctx, action="search", query="tides")
    assert brain.recent("u1", k=20, kinds=[core.ITEM_KIND]) == []
    assert brain.find_entities("u1", kind="org") == []

    plugin.run(ctx, action="info", query="tides")
    kept = brain.recent("u1", k=20, kinds=[core.ITEM_KIND])
    assert len(kept) == 1 and "Result one" in kept[0].text
    # ★그래프에 서는 것은 **채널**이다 — 영상 제목이 아니다★(2026-08-19)
    assert [e.name for e in brain.find_entities("u1", kind="org")] == ["Ch"]
    assert brain.find_entities("u1", kind="topic") == [], \
        "영상 제목이 다시 topic 노드가 되고 있습니다 — 그래프가 제목으로 찹니다"


def test_remembering_survives_a_broken_brain(tmp_path, keys, monkeypatch):
    """★기억은 부산물이다★ 브레인이 터져도 사용자는 자기 답을 받는다."""
    class _Broken:
        def __getattr__(self, name):
            raise RuntimeError("brain is down")

    plugin = YouTubePlugin()
    ctx = _Ctx(tmp_path, brain=_Broken())
    monkeypatch.setattr(plugin, "_api", lambda ctx, path, params: {"items": [
        {"id": "aaaaaaaaaaa", "snippet": {"title": "Still answers"}}]})
    answer = plugin.run(ctx, action="info", query="aaaaaaaaaaa")
    assert "Still answers" in answer
    assert any("could not remember" in line for line in ctx.logs)


def test_what_you_uploaded_is_yours_and_comes_back(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    plan = core.plan_upload("/x/clip.mp4", title="My trip", tags=["travel", "japan"],
                            privacy="unlisted", exists=lambda p: True)
    core.remember_upload(brain, "u1", core.Video(video_id="ccccccccccc"), plan)

    items = brain.find_entities("u1", kind="item")
    assert [e.name for e in items] == ["My trip"]
    assert items[0].attrs["mine"] is True and items[0].attrs["privacy"] == "unlisted"
    # ★되읽는 문★(원칙 0 ③) — 다음 업로드가 지난 제목·태그를 안다
    got = core.recall_uploads(brain, "u1")
    assert len(got) == 1
    assert {k: got[0][k] for k in ("title", "url", "tags", "privacy")} == {
        "title": "My trip", "url": "https://www.youtube.com/watch?v=ccccccccccc",
        "tags": ["travel", "japan"], "privacy": "unlisted"}
    # ★언제 올렸나★ 없으면 화면이 *"마지막 업로드로부터 며칠"* 을 말할 수 없다
    assert got[0]["uploaded_at"]


def test_things_you_own_that_are_not_uploads_stay_out_of_the_upload_history(tmp_path):
    """`item`에는 산 물건도 살고, **남의 영상**도 언젠가 여기 올 수 있다 —
    `mine` 표시가 없으면 그것을 내 업로드라고 말하게 된다.

    ⚠️ ★미끼는 두 갈래 다 있어야 한다★ 처음에는 `video_id`가 없는 물건 하나만
    두었는데, 그러면 `mine` 검사를 통째로 지우는 뮤테이션이 **그대로 빠져나갔다**
    (`video_id` 검사가 혼자 막고 있었다 — 함정 11: 방어가 두 겹이면 못 잡는다).
    """
    from cosmos.contracts.memory import Entity
    brain = LiteMemoryProvider(tmp_path / "brain")
    brain.upsert_entity("u1", Entity(name="Headphones", kind="item"))
    brain.upsert_entity("u1", Entity(
        name="Someone else's clip", kind="item",
        attrs={"video_id": "eeeeeeeeeee",
               "url": "https://www.youtube.com/watch?v=eeeeeeeeeee"}))
    assert core.recall_uploads(brain, "u1") == []


def test_seeing_it_again_is_recognised(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_video(brain, "u1",
                        core.Video(video_id="aaaaaaaaaaa", title="Tides", channel="Ch"))
    seen = core.recall_seen(brain, "u1", "aaaaaaaaaaa")
    assert seen["times"] == 1 and seen["channel"] == "Ch" and seen["last_seen"]
    # ★없는 것을 지어내지 않는다★
    assert core.recall_seen(brain, "u1", "zzzzzzzzzzz") == {}
    assert core.recall_seen(None, "u1", "aaaaaaaaaaa") == {}


# ── ★반복될 때만 성향이다★ (Sean 결정 2026-08-19) ────────────────────────────
#
# 착수 전 실측: `topic` 노드 116개 중 ★64개(55%)가 페이지 제목 모양★이었고,
# 출처는 `tool.web_search.v1` 95개였다. 이 에이전트를 옛 설계대로 켜면 **같은
# 오염을 더 붓는** 것이었다 — 영상 제목을 그대로 `topic`으로 세웠기 때문이다.

def test_one_look_is_an_event_not_a_taste(tmp_path):
    """★한 번은 사건, 반복은 성향이다★(CLAUDE.md ②)"""
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_video(brain, "u1", core.Video(video_id="a" * 11, title="One",
                                                channel="Deep Dive"))
    assert core.regulars(brain, "u1") == [], "한 번 본 채널이 성향이 됐습니다"


def test_coming_back_to_a_channel_makes_it_a_regular(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    for n in range(core.REGULAR_AFTER):
        core.remember_video(brain, "u1", core.Video(
            video_id=f"vid{n:08d}", title=f"Episode {n}", channel="Deep Dive",
            channel_id="UC-deep"), watched=True)
    rows = core.regulars(brain, "u1")
    assert [r["channel"] for r in rows] == ["Deep Dive"]
    assert rows[0]["count"] == core.REGULAR_AFTER and rows[0]["watched"] == core.REGULAR_AFTER


def test_a_channel_that_renames_itself_is_still_one_channel():
    """★이름이 아니라 id로 모은다★ 이름으로 세면 표기가 조금만 달라져도 반복이
    반복으로 안 보이고, 그러면 성향은 영영 안 선다."""
    class _Item:
        def __init__(self, meta, ts=""):
            self.meta, self.ts = meta, ts
    rows = core.watch_counts([
        _Item({"channel": "Deep Dive", "channel_id": "UC-deep"}, "2026-08-01"),
        _Item({"channel": "Deep Dive Official", "channel_id": "UC-deep"}, "2026-08-02"),
        _Item({"channel": "Other", "channel_id": "UC-other"}, "2026-08-03")])
    assert len(rows) == 2
    assert next(r for r in rows.values() if r["count"] == 2)["last"] == "2026-08-02"


def test_a_confirmed_regular_is_written_into_the_graph(tmp_path):
    """★최근 창은 밀려난다★ 반복이 한 번 확인된 것은 나중에도 참이므로 굳힌다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    for n in range(core.REGULAR_AFTER):
        core.remember_video(brain, "u1", core.Video(
            video_id=f"vid{n:08d}", title=f"Episode {n}", channel="Deep Dive",
            channel_id="UC-deep"))
    assert core.mark_regulars(brain, "u1") == ["Deep Dive"]
    node = next(e for e in brain.find_entities("u1", kind="org") if e.name == "Deep Dive")
    assert node.attrs["watches_regularly"] is True
    assert node.attrs["seen_times"] == core.REGULAR_AFTER


def test_nothing_repeated_is_never_called_a_taste(tmp_path):
    brain = LiteMemoryProvider(tmp_path / "brain")
    for n, channel in enumerate(("A", "B", "C", "D")):
        core.remember_video(brain, "u1", core.Video(
            video_id=f"vid{n:08d}", title=f"E{n}", channel=channel,
            channel_id=f"UC-{channel}"))
    assert core.mark_regulars(brain, "u1") == []
    assert all(not (e.attrs or {}).get("watches_regularly")
               for e in brain.find_entities("u1", kind="org"))


# ── 라우팅 ───────────────────────────────────────────────────────────────────

def test_playing_hands_the_url_to_the_browser_tool(tmp_path, keys):
    """★브라우저 일은 브라우저 도구가 한다★(원칙 1) — 여기서 또 열면
    기본 브라우저·권한 판정이 두 곳이 된다."""
    ctx = _Ctx(tmp_path)
    YouTubePlugin().run(ctx, action="play",
                        query="https://youtu.be/dQw4w9WgXcQ")
    assert ctx.tool_calls == [("browser_control", {
        "action": "go_to", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})]


def test_playing_words_falls_back_to_a_search_page(tmp_path, monkeypatch):
    from cosmos.core import credentials
    monkeypatch.setattr(credentials, "reveal", lambda *a, **k: None)
    ctx = _Ctx(tmp_path)
    YouTubePlugin().run(ctx, action="play", query="lofi beats")
    url = ctx.tool_calls[0][1]["url"]
    assert url == "https://www.youtube.com/results?search_query=lofi+beats"


def test_an_unknown_action_never_becomes_an_upload(tmp_path, keys, monkeypatch):
    """★올리는 것은 말한 대로만 한다★ 파일이 딸려 왔다고 업로드로 짐작하면
    되돌릴 수 없는 일이 짐작으로 일어난다.

    ⚠️ ★파일은 **진짜로 있어야** 한다★ 없는 경로를 주었더니, 짐작으로 업로드에
    들어가도 `plan_upload`가 파일 없음으로 막아 **뮤테이션이 통과했다**. 미끼가
    약하면 그물은 아무것도 재지 않는다(함정 15).
    """
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"video-bytes")
    plugin = YouTubePlugin()
    sent = []
    monkeypatch.setattr(plugin, "_send", lambda ctx, plan: sent.append(plan) or "x")
    monkeypatch.setattr(plugin, "_api", lambda ctx, path, params: {"items": []})
    plugin.run(_Ctx(tmp_path), action="publish-it", file=str(clip), query="q")
    assert sent == []


def test_the_declared_actions_and_the_table_are_the_same_list():
    """★표가 단일 진실원이다★ 선언이 표와 어긋나면 모델은 없는 것을 부르거나
    있는 것을 못 부른다."""
    described = YouTubePlugin().parameters["properties"]["action"]["description"]
    for name in core.ACTIONS:
        assert name in described


# ── ⑥ 업로드 — 실제 배선을 지나간다 ──────────────────────────────────────────

class _Resp:
    def __init__(self, payload=None, headers=None):
        self._payload = payload or {}
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_upload_walks_the_whole_wire(tmp_path, keys, monkeypatch):
    """토큰 → 자리 잡기 → 파일 밀기. ★가장 낮은 층(`requests`)에서 가로챈다★ —
    `_send`를 통째로 대역으로 주면 URL·헤더·공개 범위가 검사 밖으로 나간다."""
    import requests
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"video-bytes")
    calls: dict[str, tuple] = {}

    def _post(url, **kw):
        calls[url] = kw
        if url.endswith("/token"):
            return _Resp({"access_token": "AT"})
        return _Resp(headers={"Location": "https://upload.example/session"})

    def _put(url, **kw):
        calls[url] = kw
        return _Resp({"id": "ddddddddddd"})

    monkeypatch.setattr(requests, "post", _post)
    monkeypatch.setattr(requests, "put", _put)

    brain = LiteMemoryProvider(tmp_path / "brain")
    answer = YouTubePlugin().run(_Ctx(tmp_path, brain=brain), action="upload",
                                 file=str(clip), title="My trip", tags="travel, japan",
                                 privacy="public")

    # ① 리프레시 토큰으로 액세스 토큰을 받았다
    assert calls["https://oauth2.googleapis.com/token"]["data"]["refresh_token"] == "RTOKEN"
    # ② 자리를 잡을 때 **공개 범위가 실제로 실렸다**
    start = calls["https://www.googleapis.com/upload/youtube/v3/videos"]
    body = json.loads(start["data"])
    assert body["status"]["privacyStatus"] == "public"
    assert body["snippet"]["title"] == "My trip"
    assert body["snippet"]["tags"] == ["travel", "japan"]
    assert start["headers"]["Authorization"] == "Bearer AT"
    assert start["params"]["uploadType"] == "resumable"
    # ③ 파일은 그 자리로 갔다
    assert "https://upload.example/session" in calls
    # ④ 답이 무슨 일이 일어났는지 말한다 — 공개면 공개라고
    assert "ddddddddddd" in answer and "public" in answer
    assert "anyone with the link" in answer
    # ⑤ 브레인에 내 자산으로 남았다
    assert core.recall_uploads(brain, "u1")[0]["title"] == "My trip"


@pytest.mark.parametrize("asked,expected", [
    ("", "private"),            # 아무 말 없으면 좁게
    ("unlisted", "unlisted"),
    ("everyone", "private"),    # 모르는 낱말도 좁게
])
def test_the_privacy_that_goes_on_the_wire_is_the_one_we_decided(tmp_path, keys,
                                                                 monkeypatch,
                                                                 asked, expected):
    """★`public`만으로 재면 아무것도 재지 않는다★ 처음 이 검사는 `public`으로만
    올려서, **언제나 public을 싣는** 뮤테이션이 그대로 통과했다(함정 15). 좁은
    값으로도 재야 '우리가 정한 것이 실제로 실린다'가 증명된다.
    """
    import requests
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"x")
    seen = {}

    def _post(url, **kw):
        if url.endswith("/token"):
            return _Resp({"access_token": "AT"})
        seen["body"] = json.loads(kw["data"])
        return _Resp(headers={"Location": "https://upload.example/s"})

    monkeypatch.setattr(requests, "post", _post)
    monkeypatch.setattr(requests, "put", lambda url, **kw: _Resp({"id": "ddddddddddd"}))
    YouTubePlugin().run(_Ctx(tmp_path), action="upload", file=str(clip), privacy=asked)
    assert seen["body"]["status"]["privacyStatus"] == expected


def test_upload_stops_before_the_wire_when_the_file_is_not_there(tmp_path, keys,
                                                                 monkeypatch):
    import requests
    monkeypatch.setattr(requests, "post", lambda *a, **k: pytest.fail("must not send"))
    answer = YouTubePlugin().run(_Ctx(tmp_path), action="upload",
                                 file=str(tmp_path / "missing.mp4"))
    assert "no file at" in answer


def test_a_revoked_refresh_token_is_reported_not_swallowed(tmp_path, keys, monkeypatch):
    import requests
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"x")
    monkeypatch.setattr(requests, "post", lambda url, **kw: _Resp({}))
    answer = YouTubePlugin().run(_Ctx(tmp_path), action="upload", file=str(clip))
    assert "revoked" in answer or "access token" in answer


def test_the_summary_says_what_it_is_based_on(tmp_path, keys, monkeypatch):
    """★자막을 못 읽는다는 사실을 숨기지 않는다★(함정 44)."""
    plugin = YouTubePlugin()
    monkeypatch.setattr(plugin, "_api", lambda ctx, path, params: {"items": [
        {"id": "aaaaaaaaaaa", "snippet": {"title": "T", "description": "Long text here"}}]})
    answer = plugin.run(_Ctx(tmp_path, thought="Three sentences."),
                        action="summarize", query="aaaaaaaaaaa")
    assert "captions" in answer and "Three sentences." in answer


def test_with_no_description_it_says_it_cannot_summarize(tmp_path, keys, monkeypatch):
    plugin = YouTubePlugin()
    monkeypatch.setattr(plugin, "_api", lambda ctx, path, params: {"items": [
        {"id": "aaaaaaaaaaa", "snippet": {"title": "T", "description": ""}}]})
    answer = plugin.run(_Ctx(tmp_path), action="summarize", query="aaaaaaaaaaa")
    assert "cannot summarize" in answer


def test_network_trouble_is_reported_as_itself(tmp_path, keys, monkeypatch):
    plugin = YouTubePlugin()

    def _boom(ctx, path, params):
        raise RuntimeError("connection reset")

    monkeypatch.setattr(plugin, "_api", _boom)
    answer = plugin.run(_Ctx(tmp_path), action="search", query="x")
    assert "Could not reach YouTube" in answer and "connection reset" in answer


def test_the_agent_asks_the_vault_with_its_own_name(tmp_path, keys, monkeypatch):
    """★배선 검사★ — 이름을 잘못 넘기면 남의 열쇠를 읽거나 자기 것을 못 읽는다."""
    plugin = YouTubePlugin()
    monkeypatch.setattr(plugin, "_api", lambda ctx, path, params: {"items": []})
    plugin.run(_Ctx(tmp_path), action="search", query="x")
    assert ("youtube", "api_key") in keys


# ══ ★되읽는 문이 **불리는가**★ (Phase AG ①-2e · 2026-08-19) ═══════════════════
#
# ⚠️ 착수 전 실측: `recall_uploads`는 **테스트에서만** 불리고 제품 코드의 어느
# 자리도 안 불렀다. 문서에는 *"다음 업로드가 지난 제목·태그를 되읽어 더 잘하기
# 위한 근거"* 라고 적혀 있었는데 실제로는 한 번도 안 읽었다.
# ★만들어 놓고 잇지 않으면 없는 것과 같다★ — 이 저장소가 일곱 번 데인 자리다.
#
# 그리고 감사 도구도 속았다: 소스에서 `recall_uploads(` 를 찾는데 **정의부가**
# 걸려서 "되읽는다 O"로 셌다.

def test_the_upload_path_actually_reads_the_past_uploads(tmp_path, monkeypatch):
    """★배선까지 잰다★ 문만 검사하면 부르는 자리가 끊겨도 초록이다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plan = core.plan_upload("/x/first.mp4", title="Episode 1",
                            tags=["books", "review"], exists=lambda p: True)
    core.remember_upload(brain, "u1", core.Video(video_id="c" * 11), plan)

    plugin = YouTubePlugin()
    ctx = _Ctx(tmp_path, brain=brain)
    monkeypatch.setattr(plugin, "_have", lambda ctx: {"google": "connected"})
    monkeypatch.setattr(plugin, "_send", lambda ctx, plan: "d" * 11)
    # ★진짜 파일을 둔다★ `plan_upload`는 디스크에 묻는다(대역을 그 아래에 두면
    # 판정을 건너뛰게 되고, 그러면 이 검사는 배선이 아니라 내 상상을 잰다)
    real = tmp_path / "second.mp4"
    real.write_bytes(b"x")

    answer = plugin.run(ctx, action="upload", file=str(real), title="Episode 2")
    assert "books" in answer and "review" in answer, \
        f"지난 태그를 되읽지 않았습니다: {answer}"


def test_the_hint_says_nothing_when_there_is_nothing_to_say():
    """★없는 것을 지어내지 않는다★ 첫 업로드에 *"지난번엔..."* 은 거짓말이다."""
    plan = core.plan_upload("/x/a.mp4", title="First", exists=lambda p: True)
    assert core._past_hint([], plan) == ""
    assert core._past_hint([{"title": "Old", "tags": []}], plan) == ""
    # ★이미 붙인 태그를 다시 권하지 않는다★
    same = core.plan_upload("/x/a.mp4", title="First", tags=["books"],
                            exists=lambda p: True)
    assert core._past_hint([{"title": "Old", "tags": ["books"]}], same) == ""


def test_looking_up_a_video_reads_which_channels_you_come_back_to(tmp_path, monkeypatch):
    """★반복은 성향이다★ — 그리고 그 성향을 **읽는 자리**가 있어야 뜻이 생긴다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    for n in range(core.REGULAR_AFTER):
        core.remember_video(brain, "u1", core.Video(
            video_id=f"old{n:08d}", title=f"Old {n}", channel="Sea School",
            channel_id="UC9"))

    plugin = YouTubePlugin()
    ctx = _Ctx(tmp_path, brain=brain)
    monkeypatch.setattr(plugin, "_have", lambda ctx: {"google": "connected"})
    monkeypatch.setattr(plugin, "_api", lambda ctx, path, params: {"items": [
        {"id": "zzzzzzzzzzz",
         "snippet": {"title": "Brand new", "channelTitle": "Sea School",
                     "channelId": "UC9"}}]})
    answer = plugin.run(ctx, action="info", query="zzzzzzzzzzz")
    assert "Sea School" in answer
    assert "come back" in answer, f"반복을 되읽지 않았습니다: {answer}"


def test_a_channel_seen_once_is_not_called_a_habit(tmp_path, monkeypatch):
    """★한 번은 사건이다★ 처음 본 채널에 *"자주 보시네요"* 는 틀린 말이고,
    틀린 친밀함은 신뢰를 한 번에 깎는다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    plugin = YouTubePlugin()
    ctx = _Ctx(tmp_path, brain=brain)
    monkeypatch.setattr(plugin, "_have", lambda ctx: {"google": "connected"})
    monkeypatch.setattr(plugin, "_api", lambda ctx, path, params: {"items": [
        {"id": "zzzzzzzzzzz",
         "snippet": {"title": "First one", "channelTitle": "New Channel"}}]})
    assert "come back" not in plugin.run(ctx, action="info", query="zzzzzzzzzzz")


def test_the_purpose_says_what_the_agent_is_for():
    """★`purpose`가 있어야 무엇을 남길지가 정해진다★(원칙 0 ①)"""
    assert len(YouTubePlugin.purpose.split()) > 20
    assert YouTubePlugin.purpose != YouTubePlugin.summary
    # ★순서가 있다★ 만드는 쪽이 주다(Sean 결정) — 그것이 문장에 드러나야 한다
    assert "own" in YouTubePlugin.purpose and "upload" in YouTubePlugin.purpose.lower()


def test_the_newest_upload_comes_first(tmp_path):
    """★찍어 보고 알았다★ (2026-08-19) 그래프가 준 순서를 그대로 썼더니 화면 맨
    위가 **27일 전 것**이었고, 그것을 마지막 업로드로 읽어 *"마지막으로 올리신 지
    27일 됐어요"* 라고 **거짓을 말했다** — 실제로는 엿새 전에 올렸다.
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    for title, when in (("Older", "2026-07-01T00:00:00"),
                        ("Newest", "2026-08-13T00:00:00"),
                        ("Middle", "2026-08-01T00:00:00")):
        plan = core.plan_upload("/x/a.mp4", title=title, exists=lambda p: True)
        core.remember_upload(brain, "u1",
                             core.Video(video_id=f"{abs(hash(title)) % 10**11:011d}"),
                             plan, now=when)
    got = core.recall_uploads(brain, "u1")
    assert [row["title"] for row in got] == ["Newest", "Middle", "Older"]

    # ★자르기 **전에** 정렬한다★ 뒤에 자르면 최근 것이 잘려 나간다
    assert core.recall_uploads(brain, "u1", limit=1)[0]["title"] == "Newest"

    state = core.channel_state(brain, "u1", now="2026-08-19T00:00:00")
    assert state["since"] == 6, f"마지막 업로드를 잘못 읽었습니다: {state['since']}"


def test_the_screen_says_who_can_see_it_not_the_code_word(tmp_path):
    """★코드의 말을 그대로 내보내지 않는다★ `unlisted`는 값이지 문장이 아니다 —
    사용자가 알고 싶은 것은 **누가 볼 수 있는가**다(쇼핑의 `official_store: true`)."""
    assert core.privacy_text("unlisted") and core.privacy_text("unlisted") != "unlisted"
    assert core.privacy_text("public") != core.privacy_text("private")
    # 모르는 값은 **아무 말도 안 한다** — 지어낸 낱말이 화면에 뜨면 오류로 읽힌다
    assert core.privacy_text("weird") == "" and core.privacy_text("") == ""

    brain = LiteMemoryProvider(tmp_path / "brain")
    plan = core.plan_upload("/x/a.mp4", title="Ep", privacy="unlisted",
                            exists=lambda p: True)
    core.remember_upload(brain, "u1", core.Video(video_id="a" * 11), plan)
    blocks = YouTubePlugin().view(_Ctx(tmp_path, brain=brain))["blocks"]
    text = json.dumps(blocks, ensure_ascii=False)
    assert "unlisted" not in text, "공개 범위가 코드의 말 그대로 화면에 나옵니다"


def test_the_screen_stands_up_with_no_keys_at_all(tmp_path):
    """★열쇠가 없으면 화면까지 비는 설계는 "고장났다"로 읽힌다★

    실측: 이 에이전트가 브레인에 남긴 것이 **0건**이었다 — 여섯 액션 중 다섯이
    열쇠에 막혀 있었기 때문이다. 화면은 기억만으로 서야 하고, 거기서 **무엇을
    하면 되는지**를 읽을 수 있어야 한다.
    """
    brain = LiteMemoryProvider(tmp_path / "brain")
    screen = YouTubePlugin().view(_Ctx(tmp_path, brain=brain))
    assert screen["blocks"], "열쇠가 없다고 화면이 통째로 비었습니다"
    first = screen["blocks"][0]
    assert first["type"] == "text" and first["text"], "무엇이 막혔는지 말하지 않습니다"


def test_the_screen_never_shows_numbers_we_refused_to_store(tmp_path):
    """★조회수·구독자는 없다★ 유튜브에 물어야 아는 값이고, 없는 것을 그럴듯하게
    채우면 그 값이 화면에서 사실이 된다."""
    brain = LiteMemoryProvider(tmp_path / "brain")
    core.remember_video(brain, "u1", core.Video(
        video_id="a" * 11, title="Ep", channel="Ch", views=987654))
    text = json.dumps(YouTubePlugin().view(_Ctx(tmp_path, brain=brain))["blocks"],
                      ensure_ascii=False)
    assert "987654" not in text and "987,654" not in text


def test_it_can_stand_in_a_window_of_its_own_and_the_user_decides():
    """★곁에 두고 보는 화면이다★ (Sean 요구 2026-08-20)

    올리고 나서 며칠에 한 번 들여다보는 화면이라, 코스모스를 덮고 있을 이유가 없다.
    ⚠️ 그렇다고 창을 **강요하지 않는다** — 둘 다 선언하므로 설정에서 사용자가 고르고,
    아무것도 안 고르면 지금까지처럼 화면 안이다(옛 사용자의 화면이 안 바뀐다).
    """
    from cosmos.contracts import view as view_contract
    plugin = YouTubePlugin()
    allowed = view_contract.spaces_of(plugin)
    assert "window" in allowed, "자기 창을 못 엽니다"
    assert view_contract.chosen_space(plugin, "") == "screen", \
        "아무것도 안 골랐는데 창으로 갑니다 — 쓰던 사람의 화면이 바뀝니다"
    assert view_contract.chosen_space(plugin, "window") == "window"
