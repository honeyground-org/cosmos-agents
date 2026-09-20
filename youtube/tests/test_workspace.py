"""AG-02: 실제 사용자별 상태/브레인과 외부 I/O 경계의 회귀 검사."""
import json
from types import SimpleNamespace

import pytest

from cosmos.contracts import ToolContext
from cosmos.contracts.memory import MemoryItem
from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
from youtube_scout import YouTubePlugin, Video, watch_counts, recall_seen, _UPLOAD
from youtube_viewer import COPY, LANGS


class Context(ToolContext):
    def __init__(self, uid="sean", brain=None):
        self.uid, self.memory = uid, brain
        self.calls, self.logs = [], []

    @property
    def user_id(self):
        return self.uid

    @property
    def lang(self):
        return "ko"

    @property
    def brain(self):
        return self.memory

    def write_log(self, text, **kwargs):
        self.logs.append(text)

    def run_tool(self, tool, args):
        self.calls.append((tool, args))
        return "Browser opening requested"

    def think(self, prompt, **kwargs):
        self.prompt, self.think_options = prompt, kwargs
        return "A description-based summary."


@pytest.fixture
def contexts(tmp_path, monkeypatch):
    from cosmos.core import store, store_sqlite
    # 같은 실제 SQLite 구현을 쓰되 각 검사는 자기 임시 저장소만 건드린다.
    monkeypatch.setattr(store, "provider", lambda: store_sqlite)
    monkeypatch.setattr(store_sqlite, "db_path", lambda: tmp_path / "ops/store.db")
    store_sqlite._reset_for_tests()
    brain = LiteMemoryProvider(tmp_path / "brain")
    yield Context("sean", brain), Context("another-user", brain)
    store_sqlite._reset_for_tests()


@pytest.fixture
def plugin(monkeypatch):
    agent = YouTubePlugin()
    monkeypatch.setattr(agent, "_have", lambda ctx: {"api_key": "SECRET"})
    monkeypatch.setattr(agent, "_api", lambda ctx, path, params: {"items": [
        {"id": "aaaaaaaaaaa", "snippet": {"title": "First reference",
         "description": "A description", "channelTitle": "Example channel", "channelId": "UC-1"}}]})
    return agent


def test_results_survive_new_context_without_crossing_users(contexts, plugin):
    sean, other = contexts
    plugin.run(sean, action="search", query="reference")
    restored = Context("sean", sean.brain).load_agent_state("youtube", "workspace")
    assert restored["videos"][0]["title"] == "First reference"
    assert other.load_agent_state("youtube", "workspace") == {}
    assert not sean.brain.recent("sean", k=10, kinds=["youtube"])
    plugin.run(sean, action="info", query="aaaaaaaaaaa")
    assert recall_seen(sean.brain, "sean", "aaaaaaaaaaa")
    assert not recall_seen(sean.brain, other.user_id, "aaaaaaaaaaa")


def test_view_reads_same_results_without_network_and_has_stable_html(contexts, plugin, monkeypatch):
    sean, _ = contexts
    plugin.run(sean, action="search", query="q")
    first = plugin.view(sean)
    monkeypatch.setattr(plugin, "_api", lambda *a: pytest.fail("view called API"))
    sean.save_agent_state("youtube", {"action": "search", "videos": []}, "workspace")
    second = plugin.view(sean)
    a, b = first["blocks"][-1], second["blocks"][-1]
    assert a["type"] == "html" and a["html"] == b["html"] and a["key"] == b["key"]
    assert a["state"]["latest"]["videos"] and not b["state"]["latest"]["videos"]
    assert a["state"]["copy"]["search"] == "검색"
    assert first["refresh_ms"] == 5000
    assert "SECRET" not in json.dumps(first)


def test_reading_setup_does_not_ask_for_upload_connection(contexts, plugin):
    sean, _ = contexts
    assert plugin._connect_line(sean) == ""  # reading API key, no Google upload connection


def test_real_core_dispatch_reads_and_remembers_without_publishing_permission(contexts, plugin, monkeypatch):
    from cosmos.core import agents, autonomy, permissions
    from cosmos.core.orchestrator import Orchestrator
    from cosmos.core.personas import Persona
    from cosmos.core.registry import Registry
    sean, other = contexts
    registry = Registry()
    registry.register(plugin)
    monkeypatch.setattr(agents, "is_enabled", lambda *a, **kw: True)
    monkeypatch.setattr(agents, "hidden_names", lambda p: set())
    monkeypatch.setattr(permissions, "effective_blocked", lambda p=None: {"media.publish"})
    monkeypatch.setattr(plugin, "_upload", lambda *a: pytest.fail("upload executed"))
    engine = SimpleNamespace(registry=registry, persona=Persona(),
                             session=SimpleNamespace(user_id=sean.user_id))
    assert registry.declarations(blocked_capabilities={"media.publish"})[0]["parameters"]["properties"]["action"]["enum"] == [
        "layout", "search", "info", "summarize", "trending", "play"]
    autonomy.reset()
    try:
        for action in ("search", "info", "summarize", "trending", "play"):
            result = Orchestrator.dispatch(engine, "youtube", sean, {"action": action, "query": "aaaaaaaaaaa"})
            assert "Permission is off" not in result and not autonomy.is_held(result)
        assert recall_seen(sean.brain, sean.user_id, "aaaaaaaaaaa")
        assert not recall_seen(other.brain, other.user_id, "aaaaaaaaaaa")
        assert sean.load_agent_state("youtube", "workspace")["videos"]
        assert other.load_agent_state("youtube", "workspace") == {}
        assert autonomy.pending(sean.user_id) == []
        assert "media.publish" in Orchestrator.dispatch(engine, "youtube", sean, {"action": " UPLOAD "})
    finally:
        autonomy.reset()


def test_missing_identity_never_falls_back_to_local(plugin):
    ctx = Context("")
    assert "Sign in" in plugin.run(ctx, action="play", query="aaaaaaaaaaa")
    assert not ctx.calls
    assert "Sign in" in str(plugin.view(ctx))


def test_opening_is_only_intent_even_when_browser_denies(contexts, plugin, monkeypatch):
    sean, _ = contexts
    monkeypatch.setattr(sean, "run_tool", lambda *a: "Permission denied")
    assert "Permission denied" in plugin.run(sean, action="play", query="aaaaaaaaaaa")
    items = sean.brain.recent("sean", k=10, kinds=["youtube"])
    assert len(items) == 1
    assert items[0].meta["event"] == "open_requested"
    assert items[0].meta["watched"] is False
    assert "Watched" not in items[0].text
    assert watch_counts(items) == {}


def test_info_then_summary_same_day_is_one_visit():
    rows = [MemoryItem(text="lookup", kind="youtube", ts=t, meta={
        "channel": "Example", "channel_id": "UC-1", "video_id": v})
        for t, v in [("2026-09-08T01:00:00", "a"), ("2026-09-08T01:01:00", "a"),
                     ("2026-09-08T01:02:00", "b"), ("2026-09-09T01:00:00", "a")]]
    assert watch_counts(rows)["Example"]["count"] == 3


def test_connected_oauth_uses_core_refresh_for_this_user(contexts, plugin, monkeypatch):
    from cosmos.core import appauth
    sean, _ = contexts
    calls = []
    monkeypatch.setattr(appauth, "token_of", lambda *a, **k: "REFRESH-SECRET")
    monkeypatch.setattr(appauth, "access_token", lambda *a, **k: calls.append((a, k)) or "ACCESS")
    assert plugin._access_token(sean) == "ACCESS"
    assert calls == [(("youtube", "google"), {"user_id": "sean"})]


@pytest.mark.parametrize("status", [None, 401, 403, 429, 500])
def test_errors_never_return_secret_urls(contexts, plugin, monkeypatch, status):
    import requests
    error = requests.HTTPError("https://example?key=TOP_SECRET&refresh_token=SECRET")
    error.response = SimpleNamespace(status_code=status)
    def fail(*args):
        raise error
    monkeypatch.setattr(plugin, "_api", fail)
    ctx, _ = contexts
    answer = plugin.run(ctx, action="search", query="q")
    assert "SECRET" not in answer + str(ctx.logs)
    assert "Check" in answer


@pytest.mark.parametrize("url", ["https://evil.example/upload", "http://www.googleapis.com/upload/youtube/v3/videos",
    "https://www.googleapis.com.evil.example/upload/youtube/v3/videos", "https://u:p@www.googleapis.com/upload/youtube/v3/videos",
    "https://www.googleapis.com:444/upload/youtube/v3/videos", "https://www.googleapis.com/not-upload"])
def test_upload_never_sends_file_or_token_to_untrusted_location(contexts, plugin, monkeypatch, tmp_path, url):
    import requests
    from youtube_scout import plan_upload, YouTubeActionError
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"test video")
    monkeypatch.setattr(plugin, "_access_token", lambda ctx: "ACCESS-SECRET")
    monkeypatch.setattr(requests, "post", lambda *a, **k: SimpleNamespace(
        headers={"Location": url}, raise_for_status=lambda: None))
    monkeypatch.setattr(requests, "put", lambda *a, **k: pytest.fail("file or token leaked"))
    with pytest.raises(YouTubeActionError, match="trusted upload URL"):
        plugin._send(contexts[0], plan_upload(str(path)))


def test_no_metadata_does_not_invent_video_or_memory(contexts, plugin, monkeypatch):
    monkeypatch.setattr(plugin, "_api", lambda *args: {"items": []})
    ctx, _ = contexts
    assert "could not find" in plugin.run(ctx, action="info", query="aaaaaaaaaaa")
    assert not ctx.brain.recent("sean", k=10, kinds=["youtube"])


def test_summary_is_grounded_and_model_failure_does_not_leak(contexts, plugin, monkeypatch):
    ctx, _ = contexts
    answer = plugin.run(ctx, action="summarize", query="aaaaaaaaaaa")
    assert "no captions retrieved" in answer
    assert "untrusted" in ctx.think_options["system"] and "ko" in ctx.think_options["system"]
    assert ctx.load_agent_state("youtube", "workspace")["summary"] in answer
    def fail(*a, **kw):
        raise RuntimeError("MODEL_SECRET")
    monkeypatch.setattr(ctx, "think", fail)
    assert "MODEL_SECRET" not in plugin.run(ctx, action="summarize", query="aaaaaaaaaaa")


def test_failed_save_keeps_tool_answer_and_reports_failure(contexts, plugin, monkeypatch):
    def fail(*a):
        raise RuntimeError("STORE_SECRET")
    ctx, _ = contexts
    monkeypatch.setattr(ctx, "save_agent_state", fail)
    answer = plugin.run(ctx, action="search", query="q")
    assert "First reference" in answer and "could not be saved" in answer
    assert "STORE_SECRET" not in answer


def test_view_copy_covers_all_supported_languages():
    assert len(COPY) >= 25
    assert all(len(row) == len(LANGS) and all(row) for row in COPY.values())


def test_broken_memory_is_not_presented_as_an_empty_channel(contexts, plugin):
    class BrokenBrain:
        def find_entities(self, *a, **k): raise RuntimeError("MEMORY_SECRET")
    ctx = Context("sean", BrokenBrain())
    snapshot = plugin.view(ctx)["blocks"][-1]["state"]
    assert snapshot["warning"]
    assert "MEMORY_SECRET" not in str(snapshot)


def test_large_results_still_fit_the_view_contract():
    from youtube_viewer import block
    from cosmos.contracts.view import normalize
    huge = "😀" * 10000
    channel = {"uploads": [{"title": huge, "tags": [huge]*20, "privacy": "private"}]*12,
               "regulars": [{"channel": huge, "count": 100}]*60}
    latest = {"summary": huge, "query": huge, "videos": [{
        "id": "a"*11, "title": huge, "channel": huge, "description": huge}]*8}
    view = normalize({"blocks": [block(channel, latest)]})
    assert view["blocks"][0]["type"] == "html"
    assert len(json.dumps(view["blocks"][0]["state"], ensure_ascii=False).encode()) < 100000


def test_thumbnail_comes_from_api_evidence_and_stays_in_workspace(contexts, plugin, monkeypatch):
    from youtube_scout import normalize
    video=normalize({'items':[{'id':'aaaaaaaaaaa','snippet':{'title':'Video',
        'thumbnails':{'medium':{'url':'https://images.example/video.jpg'}}}}]})[0]
    assert video.thumbnail=='https://images.example/video.jpg'
    ctx,_=contexts
    calls=[]
    monkeypatch.setattr(ctx,'prepare_agent_images',lambda urls:(calls.append(urls) or {video.thumbnail:'data:image/jpeg;base64,EXAMPLE'}))
    assert plugin._save_results(ctx,'search','sample',[video])==''
    state=ctx.load_agent_state('youtube','workspace')
    assert state['videos'][0]['image']=='data:image/jpeg;base64,EXAMPLE'
    plugin.view(ctx);plugin.view(ctx)
    assert len(calls)==1


def test_layout_is_user_owned_persistent_and_does_not_call_services(contexts, plugin, monkeypatch):
    sean, other = contexts
    plugin.run(sean, action='search', query='reference')
    before = sean.load_agent_state('youtube', 'workspace')
    monkeypatch.setattr(plugin, '_have', lambda *a: pytest.fail('Layout must not read credentials'))
    assert '저장했습니다' in plugin.run(sean, action='layout', view_mode='research')
    assert sean.load_agent_state('youtube', 'workspace') == before
    assert other.load_agent_state('youtube', 'presentation') == {}
    again = YouTubePlugin()
    html = next(b for b in again.view(sean)['blocks'] if b['type'] == 'html')
    assert html['state']['view_mode'] == 'research'
    assert '저장했습니다' in plugin.run(sean, action='layout', view_mode='channel')
    assert sean.load_agent_state('youtube', 'presentation')['view_mode'] == 'channel'


@pytest.mark.parametrize('mode', ['fullscreen', None, {}, ['research']])
def test_invalid_layout_cannot_overwrite_the_saved_choice(contexts, plugin, mode):
    sean, _ = contexts
    plugin.run(sean, action='layout', view_mode='research')
    assert '선택해 주세요' in plugin.run(sean, action='layout', view_mode=mode)
    assert sean.load_agent_state('youtube', 'presentation')['view_mode'] == 'research'


def test_failed_layout_save_reports_failure_without_claiming_a_network_error(contexts, plugin, monkeypatch):
    sean, _ = contexts
    monkeypatch.setattr(sean, 'save_agent_state', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('PRIVATE_PATH')))
    assert plugin.run(sean, action='layout', view_mode='research') == '화면 구성을 저장하지 못했습니다. 다시 시도해 주세요.'


def test_failed_state_read_keeps_the_view_usable(contexts, plugin, monkeypatch):
    sean, _ = contexts
    monkeypatch.setattr(sean, 'load_agent_state', lambda *a, **k: (_ for _ in ()).throw(RuntimeError('PRIVATE_PATH')))
    html = next(b for b in plugin.view(sean)['blocks'] if b['type'] == 'html')
    assert html['state']['view_mode'] == 'channel'
    assert 'PRIVATE_PATH' not in str(html['state'])
    assert html['state']['warning']


def test_optional_thumbnail_failure_keeps_search_results(contexts,plugin,monkeypatch):
    ctx,_=contexts
    monkeypatch.setattr(ctx,'prepare_agent_images',lambda *a:(_ for _ in ()).throw(OSError('private')))
    answer=plugin.run(ctx,action='search',query='reference')
    assert 'First reference' in answer and 'private' not in answer
    assert ctx.load_agent_state('youtube','workspace')['videos'][0]['image']==''


def test_late_search_cannot_replace_workspace_after_network_revoked(contexts,plugin,monkeypatch):
    from cosmos.core import permissions,userstate
    ctx,_=contexts
    plugin.run(ctx,action='search',query='before')
    before=ctx.load_agent_state('youtube','workspace')
    api=plugin._api
    def late(*args,**kw):
        permissions.set_state('network','deny')
        return api(*args,**kw)
    monkeypatch.setattr(plugin,'_api',late)
    with userstate.scope(ctx.user_id):
        try:
            assert 'access changed' in plugin.run(ctx,action='search',query='after')
            assert ctx.load_agent_state('youtube','workspace')==before
        finally:permissions.set_state('network','allow')
