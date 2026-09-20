"""AG-03: real memory/state contracts, lifecycle results and action permissions."""
import json
from types import SimpleNamespace

from cosmos.contracts import ToolContext
from cosmos.runtime.memory_lite.provider import LiteMemoryProvider
from shopping_scout import ShoppingPlugin, _load, _save, _to_candidate
from shopping_core import (Candidate, cheapest_index, compare_with_past, recall_search,
                           remember_checkout, remember_search, watchlist)


class Context(ToolContext):
    def __init__(self, brain, uid='ag-alice'):
        self._brain, self.uid = brain, uid
        self.rows = [{'title': f'Candidate {i}', 'price': 10000+i*1000, 'currency': 'KRW',
                      'url': f'https://example.com/{i}', 'note': 'Verified search snippet',
                      'signals': {'rating': 4.8-i*.1}} for i in range(6)]
        self.calls, self.logs = [], []
        self.failure = False
    @property
    def user_id(self): return self.uid
    @property
    def brain(self): return self._brain
    @property
    def lang(self): return 'en'
    def run_tool(self, name, args):
        self.calls.append((name,args))
        if self.failure: raise RuntimeError('SECRET_TOKEN')
        return 'Permission denied' if name == 'browser_control' else 'Search evidence'
    def think(self, *a, **k): return json.dumps(self.rows)
    def write_log(self, line, *a, **k): self.logs.append(line)


def context(tmp_path): return Context(LiteMemoryProvider(tmp_path / 'brain'))


def test_state_persists_across_instances_without_crossing_accounts(tmp_path):
    a = context(tmp_path); agent = ShoppingPlugin()
    agent.run(a, query='Headphones', criteria='Quiet train travel')
    b = Context(a.brain, 'ag-bob')
    assert _load(b) == {}
    again = Context(a.brain)
    assert _load(again)['query'] == 'Headphones'
    agent.run(again, query='Headphones')
    assert 'Quiet train travel' in again.calls[0][1]['query']
    assert recall_search(a.brain,a.user_id,'Headphones')['criteria'] == 'Quiet train travel'
    agent.run(again, query='Headphones', criteria='')
    assert recall_search(a.brain,a.user_id,'Headphones')['criteria'] == ''
    assert not a.brain.find_entities(a.user_id,kind='preference')


def test_failed_search_preserves_old_results_but_empty_search_clears_them(tmp_path):
    ctx=context(tmp_path); agent=ShoppingPlugin(); agent.run(ctx,query='First')
    revision=_load(ctx)['revision']; ctx.failure=True
    assert 'unavailable' in agent.run(ctx,query='Second')
    assert _load(ctx)['revision']==revision
    assert 'SECRET_TOKEN' not in str(ctx.logs)
    ctx.failure=False;ctx.rows=[]
    agent.run(ctx,query='Empty')
    assert _load(ctx)['items']==[] and _load(ctx)['query']=='Empty'


def test_stale_selection_does_not_open_or_settle_a_new_item(tmp_path):
    ctx=context(tmp_path); agent=ShoppingPlugin(); agent.run(ctx,query='First')
    revision=_load(ctx)['revision'];agent.run(ctx,query='Second')
    for action in ('open','checkout','bought','dropped','next'):
        result=agent.run(ctx,action=action,index=1,revision=revision)
        assert 'changed' in result
    assert all(call[0]=='web_search' for call in ctx.calls)
    assert not recall_search(ctx.brain,ctx.user_id,'Second')['candidates'][0]['bought_at']


def test_invalid_item_number_never_marks_the_first_item_bought(tmp_path):
    ctx=context(tmp_path);agent=ShoppingPlugin();agent.run(ctx,query='First')
    for index in (0,-1,999,'bad'):
        assert 'Which one' in agent.run(ctx,action='bought',index=index)
    assert not recall_search(ctx.brain,ctx.user_id,'First')['candidates'][0]['bought_at']


def test_candidates_seen_on_later_pages_can_be_settled_and_undone(tmp_path):
    ctx=context(tmp_path);agent=ShoppingPlugin();agent.run(ctx,query='First')
    agent.run(ctx,action='next')
    assert 'yours' in agent.run(ctx,action='bought',index=5)
    rows=recall_search(ctx.brain,ctx.user_id,'First')['candidates']
    assert next(r for r in rows if r['title']=='Candidate 4')['bought_at']
    assert _load(ctx)['items'][4]['outcome']=='bought'
    agent.run(ctx,action='still_looking',index=5)
    assert not next(r for r in recall_search(ctx.brain,ctx.user_id,'First')['candidates'] if r['title']=='Candidate 4')['bought_at']


def test_deleted_memory_is_not_reported_as_successfully_settled(tmp_path):
    ctx=context(tmp_path);agent=ShoppingPlugin();agent.run(ctx,query='First')
    state=_load(ctx);state['query']='Not in memory';_save(ctx,state)
    assert 'could not write' in agent.run(ctx,action='bought',index=1)


def test_browser_denial_is_not_reported_as_opened(tmp_path):
    ctx=context(tmp_path);agent=ShoppingPlugin();agent.run(ctx,query='First')
    assert agent.run(ctx,action='open',index=1)=='Permission denied'


def test_currencies_and_product_histories_are_not_pooled(tmp_path):
    ctx=context(tmp_path);agent=ShoppingPlugin();agent.run(ctx,query='First')
    ctx.rows[0]['price']=7000;agent.run(ctx,query='First')
    assert [r['price'] for r in _load(ctx)['history']]==[10000,7000]
    past=recall_search(ctx.brain,ctx.user_id,'First')
    assert not compare_with_past(past,[Candidate('Candidate 0',10,'USD')])['changes']
    assert cheapest_index([{'price':1000,'currency':'KRW'},{'price':1,'currency':'USD'}])==-1


def test_a_confirmed_purchase_is_not_asked_again(tmp_path):
    ctx=context(tmp_path);agent=ShoppingPlugin();agent.run(ctx,query='First')
    remember_checkout(ctx.brain,ctx.user_id,'First','Candidate 0','example.com')
    agent.run(ctx,action='bought',index=1)
    past=recall_search(ctx.brain,ctx.user_id,'First')
    assert not compare_with_past(past,[Candidate('Candidate 0',9000)])['checked_out']


def test_untrusted_extraction_has_no_executable_link_or_fabricated_signal():
    row=_to_candidate({'title':'<script>alert(1)</script>','url':'javascript:alert(1)',
                       'signals':{'rating':'excellent','review_count':-1,'official_store':'yes'}})
    assert row.url=='' and row.signals=={}
    assert _to_candidate({'title':'A','signals':['bad']}).signals=={}


def test_current_view_uses_state_not_interpolated_html(tmp_path):
    ctx=context(tmp_path);ctx.rows[0]['title']='<script>window.pwned=true</script>'
    agent=ShoppingPlugin();agent.run(ctx,query='First')
    block=agent.view(ctx)['blocks'][0]
    assert block['type']=='html' and block['key']=='shopping-workspace-v1'
    assert 'window.pwned' not in block['html']
    assert 'window.pwned' in json.dumps(block['state'])
    assert 'https://example.com' not in json.dumps(block['state'])
    from shopping_viewer import COPY,LANGS
    assert all(len(row)==len(LANGS) and all(row) for row in COPY.values())


def test_denied_search_still_allows_saved_view_and_outcome_through_core(tmp_path):
    from cosmos.core import agents,permissions
    from cosmos.core.orchestrator import Orchestrator
    from cosmos.core.personas import Persona
    from cosmos.core.registry import Registry
    from cosmos.core.capabilities import required_for
    ctx=context(tmp_path);agent=ShoppingPlugin();agent.run(ctx,query='First')
    registry=Registry();registry.register(agent);agents.set_enabled('shopping',True)
    permissions.set_state('shopping.search','deny')
    engine=SimpleNamespace(registry=registry,persona=Persona(),session=SimpleNamespace(user_id=ctx.user_id))
    assert required_for(agent,view=True)=={'memory'}
    assert 'Permission is off' in Orchestrator.dispatch(engine,'shopping',ctx,{'action':'search','query':'Blocked'})
    assert 'yours' in Orchestrator.dispatch(engine,'shopping',ctx,{'action':'bought','index':1})
    permissions.set_state('shopping.search','allow')


def test_state_read_failure_does_not_look_like_an_empty_account(tmp_path):
    class Broken(Context):
        def load_agent_state(self,*a): raise RuntimeError('SECRET_TOKEN')
    ctx=Broken(context(tmp_path).brain)
    view=ShoppingPlugin().view(ctx)
    assert 'could not be read' in view['blocks'][0]['text']
    assert 'SECRET_TOKEN' not in json.dumps(view)


def test_anonymous_context_cannot_fall_back_to_local_memory(tmp_path):
    ctx=Context(context(tmp_path).brain,'')
    assert 'account is required' in ShoppingPlugin().run(ctx,query='First')
    assert not ctx.calls


def test_a_repeated_search_keeps_the_confirmed_outcome_in_the_view(tmp_path):
    ctx=context(tmp_path);agent=ShoppingPlugin();agent.run(ctx,query='First')
    agent.run(ctx,action='bought',index=1);agent.run(ctx,query='First')
    assert _load(ctx)['items'][0]['outcome']=='bought'


def test_background_notice_tracking_is_owned_by_the_current_user(tmp_path):
    from shopping_core import remember_outcome
    ctx=context(tmp_path);other=Context(ctx.brain,'ag-bob');agent=ShoppingPlugin()
    for user in (ctx,other):
        user.notices={}
        user.rows=user.rows[:1]
        user.notice=lambda key,*a,_u=user,**k: _u.notices.setdefault(key,True)
        user.clear_notice=lambda key,_u=user: _u.notices.pop(key,None)
        remember_search(user.brain,user.user_id,'First',[Candidate('Candidate 0',30000)])
        agent.advise(user)
        assert user.notices
    remember_outcome(ctx.brain,ctx.user_id,'First','Candidate 0','bought')
    agent.advise(ctx)
    assert not ctx.notices and other.notices
    assert agent._raised[other.user_id]


def test_images_are_loaded_at_search_time_and_only_saved_images_reach_view(tmp_path):
    ctx=context(tmp_path);agent=ShoppingPlugin();ctx.rows[0]['image']='https://images.example/photo.jpg'
    calls=[]
    ctx.prepare_agent_images=lambda urls: (calls.append(urls) or {urls[0]:'data:image/jpeg;base64,EXAMPLE'})
    agent.run(ctx,query='First')
    assert len(calls)==1
    assert agent.view(ctx)['blocks'][0]['state']['items'][0]['image']=='data:image/jpeg;base64,EXAMPLE'
    agent.view(ctx);agent.run(ctx,action='next');agent.view(ctx)
    assert len(calls)==1
    assert 'image_data' not in str(recall_search(ctx.brain,ctx.user_id,'First'))


def test_chart_values_match_observations_and_unknown_price_is_not_a_bar(tmp_path):
    ctx=context(tmp_path);agent=ShoppingPlugin();ctx.rows[0]['price']=0
    agent.run(ctx,query='First')
    state=agent.view(ctx)['blocks'][0]['state']
    assert state['items'][0]['amount']==0
    assert 'unknown' in state['items'][0]['price'].lower()
    assert state['history']==[]
