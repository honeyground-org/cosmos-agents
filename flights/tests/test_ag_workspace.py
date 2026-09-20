"""AG-04: actual state, memory, permission and view contracts with synthetic evidence."""
import json
from types import SimpleNamespace
import pytest
from cosmos.contracts import ToolContext
from cosmos.contracts.view import normalize
from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
import flights_scout as core
from flights_viewer import COPY, block

class Context(ToolContext):
    def __init__(self, brain, uid='flights-alice'):
        self._brain, self.uid = brain, uid
        self.rows = [dict(airline=f'Air {n}',origin='ICN',destination='Tokyo',depart='2026-10-18',
                         stops=0 if n%2==0 else 1,price=300000+n*10000,currency='KRW',
                         fare_type='round_trip',leaves='09:00',arrives='11:30',duration_minutes=150,
                         url=f'https://example.com/{n}') for n in range(6)]
        self.pages, self.calls, self.logs, self.cleared = [], [], [], []
        self.failure = False
        self.grid = [{'label':'₩250,000, Oct 19 to Oct 22'}, {'label':'$100, Oct 20 to Oct 22'},
                     {'label':'₩100,000, Oct 19 to Oct 19'}]
    @property
    def user_id(self): return self.uid
    @property
    def brain(self): return self._brain
    @property
    def lang(self): return 'en'
    def read_page(self, url, **kwargs):
        self.pages.append((url,kwargs))
        if self.failure: raise RuntimeError('SECRET_TOKEN')
        return {'ok':True,'text':'Evidence' if self.rows else '', 'targets':self.grid if kwargs.get('click') else []}
    def think(self, *a, **k): return json.dumps(self.rows)
    def run_tool(self,name,args):
        self.calls.append((name,args))
        return 'Permission denied'
    def write_log(self,line,*a,**k): self.logs.append(line)
    def clear_notice(self,key): self.cleared.append(key)

@pytest.fixture
def setup(tmp_path):
    ctx=Context(LiteMemoryProvider(tmp_path/'brain'),uid='flights-'+tmp_path.name)
    agent=core.FlightsPlugin()
    args=dict(origin='ICN',destination='Tokyo',depart='2026-10-18',return_on='2026-10-22')
    agent.run(ctx,**args)
    return agent,ctx,args

def test_real_state_isolated_and_new_instance_continues_trip(setup):
    agent,ctx,args=setup
    b=Context(ctx.brain,ctx.uid+'-bob')
    assert core._load(b)=={}
    again=Context(ctx.brain,ctx.uid)
    core.FlightsPlugin().run(again,destination='Tokyo')
    assert '2026-10-22' in again.pages[0][0]
    assert core._load(again)['return_on']=='2026-10-22'
    assert not ctx.brain.find_entities(ctx.uid,kind='preference')

def test_search_does_not_click_date_grid(setup):
    agent,ctx,args=setup
    assert all(not kwargs.get('click') for _,kwargs in ctx.pages)
    assert core._load(ctx)['nearby']==[]
    agent.run(ctx,action='nearby')
    assert ctx.pages[-1][1]['click']=='date grid'
    nearby=core._load(ctx)['nearby']
    assert len(nearby)==1 and nearby[0]['date']=='2026-10-19' and nearby[0]['currency']=='KRW'

@pytest.mark.parametrize('condition',[{'nonstop':True},{'airline':'Air 0'}])
def test_unproven_grid_filters_do_not_claim_a_cheaper_flight(setup,condition):
    agent,ctx,args=setup
    agent.run(ctx,**args,**condition)
    assert 'does not mean' in agent.run(ctx,action='nearby')
    assert core._load(ctx)['nearby']==[]

def test_failure_keeps_previous_results_empty_clears(setup):
    agent,ctx,args=setup
    revision=core._load(ctx)['revision'];ctx.failure=True
    assert 'could not' in agent.run(ctx,**args)
    assert core._load(ctx)['revision']==revision
    assert 'SECRET_TOKEN' not in json.dumps(ctx.logs)+core._load(ctx)['notice']
    ctx.failure=False;ctx.rows=[]
    agent.run(ctx,**args)
    assert core._load(ctx)['items']==[]
    assert core._load(ctx)['revision']!=revision

def test_booked_and_undo_change_memory_and_survive_next_search(setup):
    agent,ctx,args=setup
    revision=core._load(ctx)['revision']
    agent.run(ctx,action='booked',revision=revision)
    assert core.recall_route(ctx.brain,ctx.uid,trip=core.trip_of(args))['booked_at']
    assert not core.watchlist(ctx.brain,ctx.uid)
    agent.run(ctx,**args)
    assert core._load(ctx)['outcome']=='booked'
    agent.run(ctx,action='still_looking')
    assert core._load(ctx)['outcome']=='still_looking'
    assert core.watchlist(ctx.brain,ctx.uid)

def test_stale_revision_cannot_open_settle_or_page(setup):
    agent,ctx,args=setup
    old=core._load(ctx)['revision'];agent.run(ctx,**args)
    for action in ['open','booked','next','nearby','forget']:
        assert 'changed' in agent.run(ctx,action=action,index=1,revision=old)
    assert ctx.calls==[]
    assert core._load(ctx)['outcome']=='still_looking'

def test_selected_link_delegates_and_preserves_denial(setup):
    agent,ctx,args=setup
    assert agent.run(ctx,action='open',index=2)=='Permission denied'
    assert ctx.calls==[('browser_control',{'url':'https://example.com/1'})]
    for index in [0,-1,99,'bad']:
        agent.run(ctx,action='open',index=index)
    assert len(ctx.calls)==1

@pytest.mark.parametrize('url',['javascript:alert(1)','http://example.com','https://user:pass@example.com','https://example.com/\nprivate'])
def test_untrusted_link_never_leaves_tool_boundary(setup,url):
    agent,ctx,args=setup
    ctx.rows[0]['url']=url;agent.run(ctx,**args)
    assert not core._load(ctx)['items'][0]['url']
    assert 'No source link' in agent.run(ctx,action='open',index=1)
    assert ctx.calls==[]

def test_foreground_currency_and_fare_basis_never_mix():
    krw=core.Flight(price=300000,currency='KRW',fare_type='round_trip',stops=0)
    usd=core.Flight(price=300,currency='USD',fare_type='round_trip',stops=0)
    one=core.Flight(price=150000,currency='KRW',fare_type='one_way',stops=0)
    for rows in [[krw,usd],[krw,one]]:
        assert core.cheapest(rows) is None
        assert core.best_pick(rows) is None
    for past in [{'price':400000,'currency':'USD'},{'price':400000,'currency':'KRW','fare_type':'one_way'}]:
        past['seen_at']=core.now_ts()
        assert core.compare_with_past(past,[krw])['delta'] is None

def test_history_resets_when_currency_or_fare_basis_changes(setup):
    agent,ctx,args=setup
    for r in ctx.rows: r['currency']='USD';r['price']=300
    agent.run(ctx,**args)
    assert len(core._load(ctx)['history'])==1
    assert len(core.recall_route(ctx.brain,ctx.uid,trip=core.trip_of(args))['history'])==1

def test_missing_stops_is_not_nonstop():
    row=core.to_flights([{'destination':'Tokyo','price':100,'currency':'USD'}])[0]
    assert row.stops==-1 and not core.matches_trip(row,core.Trip(nonstop=True))
    assert core.best_pick([row]) is None
    assert core.stops_text(row.stops)==''

def test_other_departure_date_is_not_the_same_trip():
    assert not core.matches_trip(core.Flight(depart='2026-10-19'),core.Trip(depart='2026-10-18'))

@pytest.mark.parametrize('dates',[{'depart':'2026-02-30'}, {'depart':'2026-10-22','return_on':'2026-10-18'}])
def test_invalid_dates_make_no_external_call(setup,dates):
    agent,ctx,args=setup;ctx.pages.clear()
    agent.run(ctx,**{**args,**dates})
    assert ctx.pages==[]

def test_view_stable_bounded_and_updates_from_actions(setup):
    agent,ctx,args=setup
    first=normalize(agent.view(ctx))['blocks'][0]
    assert first['type']=='html' and len(first['state']['items'])==4
    agent.run(ctx,action='next')
    second=normalize(agent.view(ctx))['blocks'][0]
    assert first['html']==second['html'] and first['key']==second['key']
    assert [r['index'] for r in second['state']['items']]==[5,6]
    assert len(json.dumps(second['state']).encode())<100000
    assert 'url' not in second['state']['items'][0]

def test_copy_has_six_real_translations():
    assert all(len(row)==6 and all(isinstance(v,str) and v.strip() for v in row) for row in COPY.values())

def test_notice_tracking_does_not_cross_users(setup):
    agent,ctx,args=setup;b=Context(ctx.brain,ctx.uid+'-bob')
    agent._raised[ctx.uid]={'fare:mine'};agent._raised[b.uid]={'fare:other'}
    agent._clear(b,'fare:other')
    assert agent._raised[ctx.uid]=={'fare:mine'} and not ctx.cleared

def test_currency_setting_is_read_with_current_user(setup,monkeypatch):
    from cosmos.core import agent_settings
    agent,ctx,args=setup
    monkeypatch.setattr(agent_settings,'get',lambda a,k,d,*,user_id: 'USD' if user_id==ctx.uid else 'EUR')
    assert agent._currency(ctx)=='USD'

def test_action_gates_keep_search_and_view_when_browser_clicking_denied(setup,monkeypatch):
    from cosmos.core import capabilities,permissions,agents
    from cosmos.core.orchestrator import Orchestrator
    from cosmos.core.registry import Registry
    from cosmos.core.personas import Persona
    agent,ctx,args=setup
    monkeypatch.setattr(permissions,'effective_blocked',lambda p:{'browser.act'}|set(p))
    monkeypatch.setattr(agents,'is_enabled',lambda *a,**k:True)
    monkeypatch.setattr(agents,'hidden_names',lambda *a,**k:set())
    registry=Registry();registry.register(agent)
    engine=SimpleNamespace(registry=registry,persona=Persona(),session=SimpleNamespace(user_id=ctx.uid))
    ctx.pages.clear()
    assert 'Air 0' in Orchestrator.dispatch(engine,'flights',ctx,dict(action='search',**args))
    before=len(ctx.pages)
    assert 'browser.act' in Orchestrator.dispatch(engine,'flights',ctx,{'action':'nearby'})
    assert len(ctx.pages)==before
    assert capabilities.required_for(agent,view=True)=={'memory'}
    assert 'booked' in registry.declarations(blocked_capabilities={'network','browser','browser.act'})[0]['parameters']['properties']['action']['enum']

def test_manifest_and_code_declare_the_same_capabilities():
    from pathlib import Path
    import yaml
    manifest=yaml.safe_load((Path(__file__).parents[1]/'cosmos-agent.yaml').read_text())
    assert set(manifest['capabilities'])==set(core.FlightsPlugin.capabilities)

def test_round_trip_forget_does_not_delete_the_one_way_trip(setup):
    agent,ctx,args=setup
    one=core.Trip(origin='ICN',destination='Tokyo',depart='2026-10-18')
    core.remember_search(ctx.brain,ctx.uid,one.origin,one.destination,[],trip=one)
    agent.run(ctx,action='forget',**args)
    assert core._load(ctx)=={}
    assert not core.recall_route(ctx.brain,ctx.uid,trip=core.trip_of(args))
    assert core.recall_route(ctx.brain,ctx.uid,trip=one)

def test_memory_write_failure_is_visible_without_hiding_results(setup,monkeypatch):
    agent,ctx,args=setup
    monkeypatch.setattr(core,'remember_search',lambda *a,**k:'')
    assert 'could not be saved to memory' in agent.run(ctx,**args)
    assert len(core._load(ctx)['items'])==6
    assert 'could not be saved to memory' in core._load(ctx)['notice']

def test_actual_currency_setting_survives_a_new_agent_instance(setup):
    from cosmos.core import agent_settings
    agent,ctx,args=setup
    try:
        assert agent_settings.save('flights',agent,{'currency':'JPY'},user_id=ctx.uid)['ok']
        again=core.FlightsPlugin();again.run(ctx,**args)
        assert 'curr=JPY' in ctx.pages[-1][0]
    finally:
        agent_settings.save('flights',agent,{'currency':'auto'},user_id=ctx.uid)

def test_long_trip_identity_and_notice_keys_do_not_collide(setup):
    agent,ctx,args=setup
    a=core.Trip(origin='A'*70,destination='B'*70,depart='2026-10-18',return_on='2026-10-22')
    b=core.Trip(origin=a.origin,destination=a.destination,depart=a.depart,return_on='2026-10-23')
    assert len(core.route_name_of(a))<=120 and core.route_name_of(a)!=core.route_name_of(b)
    core.remember_search(ctx.brain,ctx.uid,a.origin,a.destination,[],trip=a)
    assert core.recall_route(ctx.brain,ctx.uid,trip=a)
    assert agent._notice_key(core.route_name_of(a))!=agent._notice_key(core.route_name_of(b))

def test_saved_flight_facts_follow_the_view_language_without_research(setup):
    agent,ctx,args=setup
    korean=block(core._load(ctx),lang='ko')['state']['items'][0]
    english=block(core._load(ctx),lang='en')['state']['items'][0]
    assert korean['stops_text']=='직항' and korean['duration']=='2시간 30분'
    assert english['stops_text']=='Nonstop' and english['duration']=='2h 30m'


def test_currency_uses_standard_settings_without_repricing_existing_results(setup, monkeypatch):
    from cosmos.core import agent_settings, deployment
    available = deployment.available
    monkeypatch.setattr(deployment, "available", lambda name: True if name == "session.multiuser" else available(name))
    agent, ctx, args = setup
    before = core._load(ctx)
    pages = len(ctx.pages)
    assert 'saved' in agent.run(ctx, action='settings', currency='USD', previous_currency='')
    assert len(ctx.pages) == pages
    assert core._load(ctx) == before
    state = agent.view(ctx)['blocks'][0]['state']
    assert state['currency'] == 'USD' and all(r['currency'] == 'KRW' for r in state['items'])
    assert agent_settings.snapshot('flights', agent, user_id=ctx.uid)['fields'][0]['value'] == 'USD'
    core.FlightsPlugin().run(ctx, **args)
    assert 'curr=USD' in ctx.pages[-1][0]
    assert agent._currency(Context(ctx.brain, ctx.uid+'-other')) == ''


def test_standard_currency_change_reaches_view_and_stale_edits_are_rejected(setup):
    from cosmos.core import agent_settings
    agent, ctx, _ = setup
    agent_settings.save('flights', agent, {'currency': 'JPY'}, user_id=ctx.uid)
    assert agent.view(ctx)['blocks'][0]['state']['currency'] == 'JPY'
    assert 'changed elsewhere' in agent.run(ctx, action='settings', currency='USD', previous_currency='')
    assert agent._currency(ctx) == 'JPY'
    assert 'saved' in agent.run(ctx, action='settings', currency='', previous_currency='JPY')
    assert agent._currency(ctx) == ''


@pytest.mark.parametrize('value', [None, 1, True, {}, 'CAD', 'usd'])
def test_invalid_currency_is_not_saved_or_treated_as_search(setup, value):
    agent, ctx, _ = setup
    pages = len(ctx.pages)
    assert 'Choose a currency' in agent.run(ctx, action='settings', currency=value)
    assert len(ctx.pages) == pages and agent._currency(ctx) == ''


@pytest.mark.parametrize('switch', ['agent', 'notice'])
def test_disable_during_provider_request_prevents_late_notice(setup, monkeypatch, switch):
    from cosmos.core import agents
    from cosmos.contracts import hooks
    agent, ctx, _ = setup
    agents.set_enabled('flights', True, user_id=ctx.uid)
    hooks.save(agent, {'notice': True}, user_id=ctx.uid)
    raised = []
    ctx.notice = lambda *a, **k: raised.append(a)
    before = core.watchlist(ctx.brain, ctx.uid)[0]
    original = agent._find
    def find(*a, **k):
        rows, excluded, error = original(*a, **k)
        for row in rows: row.price = 100000
        if switch == 'agent': agents.set_enabled('flights', False, user_id=ctx.uid)
        else: hooks.save(agent, {'notice': False}, user_id=ctx.uid)
        return rows, excluded, error
    monkeypatch.setattr(agent, '_find', find)
    try:
        agent._check_one(ctx, before)
        assert not raised
        assert core.watchlist(ctx.brain, ctx.uid)[0]['price'] == before['price']
        calls = len(ctx.pages)
        agent.advise(ctx)
        assert len(ctx.pages) == calls
    finally:
        agents.set_enabled('flights', True, user_id=ctx.uid)
        hooks.save(agent, {'notice': True}, user_id=ctx.uid)
