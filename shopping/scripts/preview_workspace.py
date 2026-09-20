"""실제 Cosmos HTML 렌더러/CSP 검증. 임시 DB만 사용하고 외부 요청·실제 게시를 차단한다."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ["COSMOS_HOME"] = tempfile.mkdtemp(prefix="shopping-preview-")
os.environ["COSMOS_LANG"] = "ko"
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", type=Path, default=HERE.parent.parent / "cosmos-billy")
    parser.add_argument("--port", type=int, default=8804)
    args = parser.parse_args()
    sys.path.insert(0, str(args.core))
    spec = importlib.util.spec_from_file_location("preview", args.core / "scripts/shoot_lingua_view.py")
    preview = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preview)
    preview.PROBE = preview.PROBE.replace("'lingua'", "'shopping'")
    from cosmos.contracts import ToolContext
    from cosmos.contracts.view import normalize, spaces_of, chosen_space
    from cosmos.core.agent_panel import canvas
    from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
    from shopping_scout import ShoppingPlugin
    brain = LiteMemoryProvider(Path(os.environ["COSMOS_HOME"]) / "brain")
    class Context(ToolContext):
        def __init__(self): self.query = ""
        @property
        def user_id(self): return "preview-shopping"
        @property
        def lang(self): return "ko"
        @property
        def brain(self): return brain
        def write_log(self, *a, **k): pass
        def run_tool(self, name, args):
            if name != "web_search": return "검증용 화면: 외부 브라우저와 월렛은 실행하지 않았습니다."
            self.query = args.get("query", "")
            if "error" in self.query: raise RuntimeError("SIMULATED_SECRET")
            return "Isolated example search evidence"
        def prepare_agent_images(self, urls):
            import base64
            return {url: 'data:image/jpeg;base64,' + base64.b64encode(
                (HERE / 'scripts/fixtures' / f'headphones-{int(url.rsplit("/",1)[-1])%4+1}.jpg').read_bytes()).decode()
                for url in urls if url.startswith('https://fixture.invalid/')}
        def think(self, *a, **k):
            if "empty" in self.query: return "[]"
            return json.dumps([
                {"title": title, "price": price, "currency": "KRW", "seller": seller,
                 "signals": {"rating": rating, "review_count": reviews, "official_store": official},
                 "note": note + " 사진은 제품 식별용이 아닌 예시 사진입니다.", "url": f"https://example.com/product/{n}",
                 "image": f"https://fixture.invalid/{n}"}
                for n,(title,price,seller,rating,reviews,official,note) in enumerate([
                    ("Aero Quiet — 예시",219000,"브랜드 공식점 · 예시",4.8,128,True,"통근길 소음 차단을 우선할 때 비교할 후보입니다."),
                    ("Studio Light — 예시",179000,"오디오 스토어 · 예시",4.6,94,False,"가벼운 착용감을 확인해 볼 후보입니다."),
                    ("Daily Focus — 예시",149000,"생활 오디오 · 예시",4.5,62,False,"예산을 낮추면서 기본 성능을 비교할 후보입니다."),
                    ("Travel Sound — 예시",199000,"여행 오디오 · 예시",4.4,41,False,"휴대성과 배터리 지속 시간을 확인할 후보입니다."),
                    ("Pocket Audio — 예시",129000,"포켓 스토어 · 예시",4.2,30,False,"추가 후보를 다음 쪽에서 이어 비교합니다."),
                    ("<script>window.pwned=true</script>",0,"검증용 제목",None,None,None,"비신뢰 제목의 안전한 텍스트 표시를 검증합니다.")])],ensure_ascii=False)
    ctx, agent = Context(), ShoppingPlugin()
    from types import SimpleNamespace
    from cosmos.core import agents, permissions
    from cosmos.core.orchestrator import Orchestrator
    from cosmos.core.personas import Persona
    from cosmos.core.registry import Registry
    registry = Registry(); registry.register(agent); agents.set_enabled("shopping", True)
    permissions.set_state("wallet.autofill", "deny")
    engine = SimpleNamespace(registry=registry, persona=Persona(), session=SimpleNamespace(user_id=ctx.user_id))
    from shopping_core import Candidate, remember_search
    remember_search(brain, ctx.user_id, "출퇴근용 헤드폰 — 화면 예시", [
        Candidate("Aero Quiet — 예시",249000,"KRW",seen_at="2026-09-01T10:00:00")],
        now="2026-09-01T10:00:00", criteria="25만 원 이내 · 소음 차단 · 편안한 착용감")
    agent.run(ctx,query="출퇴근용 헤드폰 — 화면 예시")

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
                return self._json({"ok": True, "agent": "shopping", "agents": [{"agent": "shopping", "title": "Shopping"}], "view": view()})
            return super().do_GET()
        def do_POST(self):
            if self.path != "/api/agent/action": return super().do_POST()
            payload = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
            action = payload.get("args", {})
            if payload.get("tool") != "shopping" or action.get("action") not in ("search", "next", "prev", "bought", "dropped", "still_looking", "open", "settings"):
                return self._json({"ok": False, "error": "Preview action denied"})
            result = Orchestrator.dispatch(engine, "shopping", ctx, action)
            return self._json({"ok": True, "result": result, "view": view()})
    server = preview.http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Isolated preview: http://127.0.0.1:{args.port}", flush=True)
    try: server.serve_forever()
    finally: server.server_close()


if __name__ == "__main__": main()
