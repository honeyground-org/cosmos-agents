"""실제 Cosmos HTML 렌더러/CSP 검증. 임시 DB만 사용하고 외부 요청·실제 게시를 차단한다."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ["COSMOS_HOME"] = tempfile.mkdtemp(prefix="youtube-preview-")
os.environ["COSMOS_LANG"] = "ko"
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", type=Path, default=HERE.parent.parent / "cosmos-billy")
    parser.add_argument("--port", type=int, default=8803)
    args = parser.parse_args()
    sys.path.insert(0, str(args.core))
    spec = importlib.util.spec_from_file_location("preview", args.core / "scripts/shoot_lingua_view.py")
    preview = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preview)
    preview.PROBE = preview.PROBE.replace("'lingua'", "'youtube'")
    from cosmos.contracts import ToolContext
    from cosmos.contracts.view import normalize, spaces_of, chosen_space
    from cosmos.core.agent_panel import canvas
    from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
    from youtube_scout import YouTubePlugin, remember_upload, Video, plan_upload

    brain = LiteMemoryProvider(Path(os.environ["COSMOS_HOME"]) / "brain")
    class Context(ToolContext):
        @property
        def user_id(self): return "preview-sean"
        @property
        def lang(self): return "ko"
        @property
        def brain(self): return brain
        def write_log(self, *a, **k): pass
        def prepare_agent_images(self, urls):
            import base64
            fixture = HERE.parent / 'shopping/scripts/fixtures/headphones-2.jpg'
            return {url: 'data:image/jpeg;base64,' + base64.b64encode(fixture.read_bytes()).decode()
                    for url in urls if url.startswith('https://fixture.invalid/')}
        def think(self, *a, **k): return "설명 기반 검증용 요약입니다. 실제 모델을 호출하지 않았습니다."
        def run_tool(self, *a, **k): return "Preview: browser opening requested; no external browser was opened."
    ctx, agent = Context(), YouTubePlugin()
    # 실제 코어의 게시 거부 상태로 검색/상세/요약이 동작하는지 검증한다.
    from types import SimpleNamespace
    from cosmos.core import agents, permissions
    from cosmos.core.orchestrator import Orchestrator
    from cosmos.core.personas import Persona
    from cosmos.core.registry import Registry
    registry = Registry()
    registry.register(agent)
    agents.set_enabled("youtube", True)
    permissions.set_state("media.publish", "deny")
    engine = SimpleNamespace(registry=registry, persona=Persona(),
                             session=SimpleNamespace(user_id=ctx.user_id))
    agent._have = lambda ctx: {"google": "preview-only"}
    def api(ctx, path, params):
        if params.get("q") == "empty": return {"items": []}
        if params.get("q") == "error": raise RuntimeError("SIMULATED_SECRET")
        ids = [params["id"]] if "id" in params else ["aaaaaaaaaaa", "bbbbbbbbbbb"]
        return {"items": [{"id": ident, "snippet": {
            "title": "헤드폰 선택 전, 소리를 비교하는 방법" if ident.startswith("a") else "<script>alert('unsafe')</script>",
            "description": "이것은 UI 검증용 데이터입니다. 실제 영상이나 사용자 데이터가 아닙니다.",
            "channelTitle": "검증용 채널", "channelId": "UC-preview",
            "thumbnails": {"medium": {"url": "https://fixture.invalid/thumbnail"}}}} for ident in ids]}
    agent._api = api
    for i in range(3):
        plan = plan_upload("/preview.mp4", title=f"검증용 에피소드 {i+1}", tags=["대화", "일상"],
                           privacy=("private", "unlisted", "public")[i], exists=lambda p: True)
        remember_upload(brain, ctx.user_id, Video(video_id=str(i)*11), plan, now=f"2026-09-0{i+1}T09:00:00")

    def view():
        data = normalize(agent.view(ctx))
        data["space"] = {"allowed": list(spaces_of(agent)), "chosen": chosen_space(agent)}
        preview._view_json = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
        return data
    view()

    class Handler(preview._Handler):
        def end_headers(self):
            if self.path.startswith("/api/agent/canvas"):
                from shells.web.server import PANEL_CSP_DIRECTIVES
                self.send_header("Content-Security-Policy", "; ".join(f"{k} {v}" for k, v in PANEL_CSP_DIRECTIVES.items()))
            if self.path.startswith("/fonts/"): self.send_header("Access-Control-Allow-Origin", "*")
            super().end_headers()
        def do_GET(self):
            if self.path == "/gate-preview":
                return self._blob((preview.APP.parent / "gate.html").read_bytes(), "text/html; charset=utf-8")
            if self.path == "/base.css":
                return self._blob((preview.APP.parent / "base.css").read_bytes(), "text/css")
            if self.path.startswith("/vendor/"):
                root = preview.APP.parent.resolve()
                path = (root / self.path.split("?", 1)[0].lstrip("/")).resolve()
                if path.is_relative_to(root) and path.is_file() and path.suffix == ".js":
                    return self._blob(path.read_bytes(), "text/javascript")
                return self._empty(404)
            if self.path.startswith("/api/agent/canvas"):
                return self._blob(canvas().encode(), "text/html; charset=utf-8")
            if self.path.startswith("/api/agent/view"):
                return self._json({"ok": True, "agent": "youtube", "agents": [{"agent": "youtube", "title": "YouTube"}], "view": view()})
            return super().do_GET()
        def do_POST(self):
            if self.path != "/api/agent/action": return super().do_POST()
            payload = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
            action = payload.get("args", {})
            if payload.get("tool") != "youtube" or action.get("action") not in ("layout", "search", "info", "summarize", "trending", "play"):
                return self._json({"ok": False, "error": "Preview action denied"})
            result = Orchestrator.dispatch(engine, "youtube", ctx, action)
            return self._json({"ok": True, "result": result, "view": view()})
    server = preview.http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Isolated preview: http://127.0.0.1:{args.port}", flush=True)
    try: server.serve_forever()
    finally: server.server_close()


if __name__ == "__main__": main()
