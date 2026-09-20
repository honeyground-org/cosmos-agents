"""Exercise the real installer/loader/control plane using a local source archive."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile
from types import SimpleNamespace

HERE = Path(__file__).resolve().parents[1]
CORE = HERE.parents[1] / 'cosmos-billy'
os.environ['COSMOS_HOME'] = tempfile.mkdtemp(prefix='youtube-install-validation-')
os.environ['COSMOS_LANG'] = 'en'
sys.path.insert(0, str(CORE))

from cosmos.contracts import ToolContext, hooks
from cosmos.core import agents, userstate
from cosmos.core.config import settings
from cosmos.core.control import ControlPlane
from cosmos.core.market import install, spec
from cosmos.core.orchestrator import Orchestrator
from cosmos.core.personas import Persona
from cosmos.core.registry import Registry

manifest = spec.load_manifest_file(HERE / 'cosmos-agent.yaml')['manifest']
entry = {key: manifest[key] for key in ('id','type','version','contract','title','description','author','capabilities','requires')}
entry.update(repo='https://github.com/honeyground-org/cosmos-agents',ref='youtube-local-validation',path='youtube')
entry = spec.validate_index_entry(entry, official=True)['entry']
buf = io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in HERE.rglob('*'):
        relative=path.relative_to(HERE)
        if path.is_file() and not set(relative.parts)&{'tests','scripts','__pycache__','.pytest_cache'}:
            archive.write(path,'bundle/youtube/'+relative.as_posix())
install._download = lambda url: buf.getvalue()  # Only transport is replaced; no network.
from cosmos.core.market import catalog
catalog.read_catalog = lambda **kwargs: {'entries':[entry]}
reg=Registry();events=[]
engine=SimpleNamespace(registry=reg,persona=Persona(),session=SimpleNamespace(user_id='local'),request_reconnect=lambda reason:events.append(reason))
control=ControlPlane(engine)
class Context(ToolContext):
    @property
    def user_id(self):return 'local'
    @property
    def lang(self):return 'en'
    @property
    def brain(self):return None
    def write_log(self,*args,**kwargs):pass
    def run_tool(self,*args,**kwargs):raise AssertionError('No external tools in installation validation')
ctx=Context();engine.tool_context=lambda:ctx;checks=[]
with userstate.scope(ctx.user_id):
    assert settings.agents_dir.is_relative_to(Path(os.environ['COSMOS_HOME']))
    disclosure=control.manage_agent(dict(op='install',id=entry['id']))
    assert disclosure.get('needs_approval') and not reg.get('youtube')
    result=control.manage_agent(dict(op='install',id=entry['id'],approve=True))
    assert result['ok'] and not result['load']['failed'],result
    plugin=reg.get('youtube');assert plugin and plugin.market_id==entry['id']
    control.set_agent_enabled(dict(name='youtube',enabled=True))
    view=control.read_agent_view('youtube')
    assert view['ok'] and any(b['type']=='html' for b in view['view']['blocks']),view
    checks.append('real archive install, loader attachment and full control-plane view')
    from cosmos.core import permissions
    permissions.set_state('media.publish','deny')
    permissions.set_state('network','deny')
    reply=Orchestrator.dispatch(engine,'youtube',ctx,dict(action='layout',view_mode='research'))
    assert 'saved' in reply,reply
    checks.append('layout saves without network or publishing permission')
    saved=control.save_agent_settings(dict(agent='youtube',values={'region':'JP','default_privacy':'private'},space='window'))
    assert saved['ok'] and saved['space']['chosen']=='window'
    assert {f['id'] for f in saved['fields']}=={'api_key','google','region','default_privacy'}
    assert all(not f.get('filled') for f in saved['fields'] if f['kind']=='secret')
    assert control.read_agent_view('youtube')['view']['space']=={'allowed':['screen','window','browser'],'chosen':'window'}
    control.save_agent_settings(dict(agent='youtube',space='browser'))
    assert control.read_agent_view('youtube')['view']['space']['chosen']=='browser'
    control.save_agent_settings(dict(agent='youtube',space='window'))
    checks.append('existing settings, masked secrets and screen/window/browser placement')
    control.set_agent_enabled(dict(name='youtube',enabled=False))
    reply=Orchestrator.dispatch(engine,'youtube',ctx,dict(action='layout',view_mode='channel'))
    assert 'switched off' in reply and not hooks.enabled(plugin,'view',ctx.user_id)
    assert not control.read_agent_view('youtube')['ok']
    assert ctx.load_agent_state('youtube','presentation')['view_mode']=='research'
    control.set_agent_enabled(dict(name='youtube',enabled=True))
    assert hooks.enabled(plugin,'view',ctx.user_id) and control.read_agent_view('youtube')['ok']
    checks.append('off blocks actions and view; on restores the view')
    assert control.manage_agent(dict(op='remove',id=entry['id']))['ok']
    assert reg.get('youtube') is None and not spec.agent_dir(entry['id']).exists()
    assert 'Unknown tool' in Orchestrator.dispatch(engine,'youtube',ctx,{})
    assert 'youtube' not in Registry().discover_installed().names()
    checks.append('remove detaches package and tool; fresh registry excludes it')
    installed=control.manage_agent(dict(op='install',id=entry['id'],approve=True))
    assert installed['ok'] and not installed['load']['failed'],installed
    control.set_agent_enabled(dict(name='youtube',enabled=True))
    settings_after=control.read_agent_settings('youtube')
    assert settings_after['space']['chosen']=='window'
    assert next(f for f in settings_after['fields'] if f['id']=='region')['value']=='JP'
    html=next(b for b in control.read_agent_view('youtube')['view']['blocks'] if b['type']=='html')
    assert html['state']['view_mode']=='research'
    checks.append('reinstall retains layout, region and chosen display placement')
    assert control.manage_agent(dict(op='remove',id=entry['id']))['ok']
report={'agent':entry['id'],'isolated':True,'source':'local development archive','real_external_requests':False,'checks':checks,'limits':['No installer button clicks or published-version update','No Google account connection, real search or uploads','Removal retains personal memory and preferences','Browser sign-in is separate; real cross-browser login is not verified']}
out=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/youtube-install-validation.json')
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
