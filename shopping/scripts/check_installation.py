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
os.environ['COSMOS_HOME'] = tempfile.mkdtemp(prefix='shopping-install-validation-')
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
entry.update(repo='https://github.com/honeyground-org/cosmos-agents',ref='shopping-local-validation',path='shopping')
entry = spec.validate_index_entry(entry, official=True)['entry']
buf = io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as archive:
    for path in HERE.rglob('*'):
        relative=path.relative_to(HERE)
        if path.is_file() and not set(relative.parts)&{'tests','scripts','__pycache__','.pytest_cache'}:
            archive.write(path,'bundle/shopping/'+relative.as_posix())
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
ctx=Context();values=dict(price_checks=False,check_hours=24,drop_percent=15)
checks=[]
with userstate.scope(ctx.user_id):
    assert settings.agents_dir.is_relative_to(Path(os.environ['COSMOS_HOME']))
    disclosure=control.manage_agent(dict(op='install',id=entry['id']))
    assert disclosure.get('needs_approval') and not reg.get('shopping');checks.append('disclosure before install')
    result=control.manage_agent(dict(op='install',id=entry['id'],approve=True))
    assert result['ok'] and not result['load']['failed'],result
    plugin=reg.get('shopping');assert plugin and plugin.market_id==entry['id'];checks.append('real archive install and loader attachment')
    control.set_agent_enabled(dict(name='shopping',enabled=True))
    reply=Orchestrator.dispatch(engine,'shopping',ctx,dict(action='settings',preferences=values))
    assert 'saved' in reply,reply;checks.append('enabled agent saves settings')
    control.set_agent_enabled(dict(name='shopping',enabled=False))
    reply=Orchestrator.dispatch(engine,'shopping',ctx,dict(action='settings',preferences={**values,'check_hours':6}))
    assert not hooks.enabled(plugin,'notice',ctx.user_id)
    assert 'switched off' in reply
    assert ctx.load_agent_state('shopping','preferences')['check_hours']==24;checks.append('disabled dispatch cannot mutate settings or run its notice hook')
    control.set_agent_enabled(dict(name='shopping',enabled=True))
    assert hooks.enabled(plugin,'notice',ctx.user_id)
    view=reg.get('shopping').view(ctx,_tab='settings')['blocks'][0]['state']
    assert view['preferences']['drop_percent']==15 and view['open_settings'];checks.append('enable restores settings; view accepts settings parameters')
    removed=control.manage_agent(dict(op='remove',id=entry['id']))
    assert removed['ok'] and reg.get('shopping') is None and not spec.agent_dir(entry['id']).exists()
    assert 'Unknown tool' in Orchestrator.dispatch(engine,'shopping',ctx,{})
    checks.append('remove deletes package and detaches callable tool')
    assert 'shopping' not in Registry().discover_installed().names();checks.append('restart registry excludes removed tool')
    reinstall=control.manage_agent(dict(op='install',id=entry['id'],approve=True))
    assert reinstall['ok'] and not reinstall['load']['failed'],reinstall
    control.set_agent_enabled(dict(name='shopping',enabled=True))
    restored=reg.get('shopping').view(ctx)['blocks'][0]['state']['preferences']
    assert restored['drop_percent']==15 and restored['check_hours']==24
    checks.append('reinstall retains personal comparison preferences')
    assert control.manage_agent(dict(op='remove',id=entry['id']))['ok']
report={'agent':entry['id'],'source':'local development archive','isolated':True,'real_external_requests':False,'checks':checks,'preferences_after_reinstall':{k:v for k,v in restored.items() if k!='revision'},'limits':['UI installer clicks are not part of this control-plane check','The current shell does not automatically forward settings_at; expand settings in the Shopping view','Downloaded release/update version not tested','Removal detaches the agent; personal memory and component state are retained','External service search/login/purchase remain deferred']}
out=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/shopping-install-validation.json')
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
