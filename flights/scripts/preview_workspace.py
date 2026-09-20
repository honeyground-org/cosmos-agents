"""실제 Cosmos HTML 렌더러/CSP 검증. 임시 DB만 사용하고 외부 요청·실제 게시를 차단한다."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ["COSMOS_HOME"] = tempfile.mkdtemp(prefix="flights-preview-")
os.environ["COSMOS_LANG"] = "ko"
HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", type=Path, default=HERE.parent.parent / "cosmos-billy")
    parser.add_argument("--port", type=int, default=8805)
    args = parser.parse_args()
    sys.path.insert(0, str(args.core))
    spec = importlib.util.spec_from_file_location("preview", args.core / "scripts/shoot_lingua_view.py")
    preview = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(preview)
    preview.PROBE = preview.PROBE.replace("'lingua'", "'flights'")
    from cosmos.contracts import ToolContext
    from cosmos.contracts.view import normalize, spaces_of, chosen_space
    from cosmos.core.agent_panel import canvas
    from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
    from flights_scout import FlightsPlugin
    brain = LiteMemoryProvider(Path(os.environ["COSMOS_HOME"]) / "brain")
    class Context(ToolContext):
        def __init__(self): self.query = ""; self.depart = "2026-10-18"
        @property
        def user_id(self): return "preview-flights"
        @property
        def lang(self): return "ko"
        @property
        def brain(self): return brain
        def write_log(self, *a, **k): pass
        def run_tool(self, name, args):
            return "검증용 화면: 외부 브라우저를 열거나 예약하지 않았습니다."
        def read_page(self, url, **kwargs):
            from urllib.parse import urlsplit, parse_qs
            import re
            self.query = parse_qs(urlsplit(url).query).get('q',[''])[0]
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", self.query)
            self.depart = dates[0] if dates else ""
            if 'error' in self.query.casefold():
                raise RuntimeError("SIMULATED_SECRET")
            return {'ok': True, 'text': '' if 'empty' in self.query.casefold() else 'Isolated flight listing',
                    'targets': [{'label': '₩248,000, Oct 19 to Oct 22'}, {'label':'₩260,000, Oct 20 to Oct 22'}] if kwargs.get('click') else []}
        def think(self, *a, **k):
            if 'empty' in self.query.casefold(): return '[]'
            return json.dumps([
                {'airline':name,'origin':'ICN','destination':'Tokyo','depart':self.depart,
                 'leaves':leaves,'arrives':arrives,'duration_minutes':minutes,'stops':stops,
                 'price':price,'currency':'KRW','fare_type':'round_trip',
                 'url':f'https://example.com/flight/{n}',
                 'note':'화면 검토용 가상 항공편·운임입니다. 실제 운항 정보가 아닙니다.'}
                for n,(name,leaves,arrives,minutes,stops,price) in enumerate([
                 ('Korean Air','09:10','11:35',145,0,348000),
                 ('Asiana Airlines','13:20','15:50',150,0,382000),
                 ('Peach Aviation','07:45','13:50',365,1,278000),
                 ('Jeju Air','16:15','18:55',160,0,369000),
                 ('<script>window.pwned=true</script>','19:05','21:40',155,0,398000),
                ])],ensure_ascii=False)
    ctx, agent = Context(), FlightsPlugin()
    from types import SimpleNamespace
    from cosmos.core import agents, permissions
    from cosmos.core.orchestrator import Orchestrator
    from cosmos.core.personas import Persona
    from cosmos.core.registry import Registry
    registry = Registry(); registry.register(agent); agents.set_enabled("flights", True)
    # Only the isolated fake date grid is delegated; no browser/account exists here.
    from cosmos.contracts import autonomy as consent
    consent.delegate(agent, "browser.act", user_id=ctx.user_id)
    engine = SimpleNamespace(registry=registry, persona=Persona(), session=SimpleNamespace(user_id=ctx.user_id))
    from flights_scout import Flight, Trip, remember_search
    trip = Trip(origin='ICN',destination='Tokyo',depart='2026-10-18',return_on='2026-10-22')
    for stamp,price in [('2026-09-01T10:00:00',329000),('2026-09-05T10:00:00',305000)]:
        remember_search(brain, ctx.user_id, trip.origin, trip.destination,
                        [Flight(airline='Example',origin='ICN',destination='Tokyo',price=price,currency='KRW',fare_type='round_trip',seen_at=stamp)],trip=trip,now=stamp)
    agent.run(ctx,action='search',origin=trip.origin,destination=trip.destination,depart=trip.depart,return_on=trip.return_on)
    agent.run(ctx,action='nearby')

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
                return self._json({"ok": True, "agent": "flights", "agents": [{"agent": "flights", "title": "Flights"}], "view": view()})
            return super().do_GET()
        def do_POST(self):
            if self.path != "/api/agent/action": return super().do_POST()
            payload = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
            action = payload.get("args", {})
            if payload.get("tool") != "flights" or action.get("action") not in ("settings", "search", "next", "prev", "booked", "dropped", "still_looking", "open", "nearby"):
                return self._json({"ok": False, "error": "Preview action denied"})
            result = Orchestrator.dispatch(engine, "flights", ctx, action)
            return self._json({"ok": True, "result": result, "view": view()})
    server = preview.http.server.ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Isolated preview: http://127.0.0.1:{args.port}", flush=True)
    try: server.serve_forever()
    finally: server.server_close()


if __name__ == "__main__": main()
