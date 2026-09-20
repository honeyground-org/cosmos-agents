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
os.environ['COSMOS_HOME'] = tempfile.mkdtemp(prefix='flights-install-validation-')
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
entry.update(repo='https://github.com/honeyground-org/cosmos-agents',ref='flights-local-validation',path='flights')
entry = spec.validate_index_entry(entry, official=True)['entry']
buf = io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in HERE.rglob('*'):
        relative=path.relative_to(HERE)
        if path.is_file() and not set(relative.parts)&{'tests','scripts','__pycache__','.pytest_cache'}:
            archive.write(path,'bundle/flights/'+relative.as_posix())
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
ctx=Context();checks=[]
with userstate.scope(ctx.user_id):
    assert settings.agents_dir.is_relative_to(Path(os.environ['COSMOS_HOME']))
    disclosure=control.manage_agent(dict(op='install',id=entry['id']))
    assert disclosure.get('needs_approval') and not reg.get('flights')
    checks.append('disclosure before install')
    result=control.manage_agent(dict(op='install',id=entry['id'],approve=True))
    assert result['ok'] and not result['load']['failed'],result
    plugin=reg.get('flights');assert plugin and plugin.market_id==entry['id']
    control.set_agent_enabled(dict(name='flights',enabled=True))
    assert plugin.view(ctx)['blocks'][0]['type']=='html'
    checks.append('real archive install, loader attachment and HTML view')
    saved=control.save_agent_settings(dict(agent='flights',values={'currency':'USD'}))
    assert saved['saved']==['currency'] and plugin._currency(ctx)=='USD'
    assert plugin.view(ctx)['blocks'][0]['state']['currency']=='USD'
    checks.append('standard settings save is reflected in result view')
    reset=control.save_agent_settings(dict(agent='flights',values={'currency':'auto'}))
    assert reset['saved']==['currency'] and plugin._currency(ctx)==''
    control.save_agent_settings(dict(agent='flights',values={'currency':'USD'}))
    checks.append('standard settings can restore the listing default')
    reply=Orchestrator.dispatch(engine,'flights',ctx,dict(action='settings',currency='JPY',previous_currency='USD'))
    assert 'saved' in reply,reply
    assert control.read_agent_settings('flights')['fields'][0]['value']=='JPY'
    checks.append('result settings action is reflected in standard settings')
    control.set_agent_enabled(dict(name='flights',enabled=False))
    reply=Orchestrator.dispatch(engine,'flights',ctx,dict(action='settings',currency='KRW'))
    assert 'switched off' in reply and plugin._currency(ctx)=='JPY'
    assert not hooks.enabled(plugin,'notice',ctx.user_id)
    checks.append('off blocks dispatch and notice eligibility')
    control.set_agent_enabled(dict(name='flights',enabled=True))
    assert hooks.enabled(plugin,'notice',ctx.user_id)
    control.save_agent_settings(dict(agent='flights',hooks={'notice':False}))
    assert not hooks.enabled(plugin,'notice',ctx.user_id)
    assert plugin.view(ctx)['blocks'][0]['state']['currency']=='JPY'
    control.save_agent_settings(dict(agent='flights',hooks={'notice':True}))
    assert hooks.enabled(plugin,'notice',ctx.user_id)
    checks.append('notice can be disabled independently; on restores eligibility')
    removed=control.manage_agent(dict(op='remove',id=entry['id']))
    assert removed['ok'] and reg.get('flights') is None and not spec.agent_dir(entry['id']).exists()
    assert 'Unknown tool' in Orchestrator.dispatch(engine,'flights',ctx,{})
    assert 'flights' not in Registry().discover_installed().names()
    checks.append('remove deletes package and callable tool; restart excludes it')
    reinstall=control.manage_agent(dict(op='install',id=entry['id'],approve=True))
    assert reinstall['ok'] and not reinstall['load']['failed'],reinstall
    control.set_agent_enabled(dict(name='flights',enabled=True))
    restored=reg.get('flights').view(ctx)['blocks'][0]['state']['currency']
    assert restored=='JPY'
    checks.append('reinstall retains the standard currency preference')
    assert control.manage_agent(dict(op='remove',id=entry['id']))['ok']
report={'agent':entry['id'],'source':'local development archive','isolated':True,'real_external_requests':False,'checks':checks,'currency_after_reinstall':restored,'limits':['Installer UI clicks and published release updates not tested','Removal detaches the agent; personal memory and settings remain','Running provider requests are not cancelled by disabling the agent','External search/login/booking and user acceptance remain deferred']}
out=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/flights-install-validation.json')
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
