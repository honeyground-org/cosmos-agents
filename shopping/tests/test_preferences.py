"""User controls affect real checks; saved settings survive comparison refreshes."""
from datetime import datetime, timedelta
from types import SimpleNamespace
import pytest
from test_ag_workspace import Context, context as _context
from shopping_scout import ShoppingPlugin, _preferences
from shopping_core import Candidate, worth_interrupting


def context(tmp_path):
    ctx = _context(tmp_path)
    ctx.uid = "preferences-" + tmp_path.name
    return ctx


def save(ctx, **values):
    values = {**dict(price_checks=True, check_hours=12, drop_percent=7), **values}
    return ShoppingPlugin().run(ctx, action='settings', preferences=values)


def test_settings_survive_search_empty_results_and_new_context(tmp_path):
    ctx=context(tmp_path);p=ShoppingPlugin()
    assert 'saved' in save(ctx, check_hours=24, drop_percent=15)
    assert not ctx.calls
    p.run(ctx,query='Headphones');ctx.rows=[];p.run(ctx,query='Empty')
    again=Context(ctx.brain,ctx.user_id)
    assert _preferences(again)['check_hours']==24 and _preferences(again)['drop_percent']==15
    assert _preferences(Context(ctx.brain,'another-user'))['check_hours']==12
    assert p.view(ctx,_tab='settings')['blocks'][0]['state']['open_settings']


def test_background_off_does_not_search_and_clears_owned_notice(tmp_path):
    ctx=context(tmp_path);p=ShoppingPlugin();cleared=[]
    ctx.clear_notice=lambda key:cleared.append(key)
    p._raised[ctx.user_id]={'price-fixture'}
    p.run(ctx,action='settings',preferences=dict(price_checks=False,check_hours=12,drop_percent=7))
    p.advise(ctx)
    assert not ctx.calls and cleared==['price-fixture']


def test_interval_controls_when_a_check_is_due(tmp_path,monkeypatch):
    import shopping_scout as module
    ctx=context(tmp_path);ctx.notice=lambda *a,**k:True;seen=[]
    row={'query':'Headphones','last_checked':(datetime.now()-timedelta(hours=13)).isoformat()}
    monkeypatch.setattr(module,'watchlist',lambda *a:[row])
    p=ShoppingPlugin();monkeypatch.setattr(p,'_check_one',lambda *a:seen.append(True))
    save(ctx,check_hours=24);p.advise(ctx);assert not seen
    save(ctx,check_hours=12);p.advise(ctx);assert seen==[True]


def test_usd_alert_does_not_require_a_three_thousand_dollar_drop(tmp_path,monkeypatch):
    import shopping_scout as module
    ctx=context(tmp_path);p=ShoppingPlugin();notices=[];ctx.notice=lambda *a,**k:notices.append(a)
    monkeypatch.setattr(p,'_find',lambda *a:[Candidate('Headphones',80,'USD')])
    monkeypatch.setattr(module,'remember_search',lambda *a,**k:None)
    monkeypatch.setattr(module,'remember_check',lambda *a,**k:None)
    row=dict(watching=dict(title='Headphones',price=100,currency='USD'),query='Headphones',last_alert='',wish_id='fixture')
    monkeypatch.setattr(module,'watchlist',lambda *a:[row])
    p._check_one(ctx,row);assert len(notices)==1
    notices.clear();save(ctx,drop_percent=20)
    monkeypatch.setattr(p,'_find',lambda *a:[Candidate('Headphones',85,'USD')])
    p._check_one(ctx,row);assert not notices
    assert not worth_interrupting(10000,8000,min_ratio=.07,min_delta=3000)['tell']


@pytest.mark.parametrize('values',[{},dict(price_checks='false',check_hours=12,drop_percent=7),dict(price_checks=True,check_hours=1,drop_percent=7),dict(price_checks=True,check_hours=12,drop_percent=1)])
def test_invalid_preferences_do_not_change_settings(tmp_path,values):
    ctx=context(tmp_path);before=_preferences(ctx)
    ShoppingPlugin().run(ctx,action='settings',preferences=values)
    assert _preferences(ctx)==before


def test_stale_settings_cannot_overwrite_another_change(tmp_path):
    ctx=context(tmp_path);old=_preferences(ctx)['revision'];save(ctx,drop_percent=15)
    reply=ShoppingPlugin().run(ctx,action='settings',preferences=dict(price_checks=False,check_hours=12,drop_percent=7),preferences_revision=old)
    assert 'changed elsewhere' in reply and _preferences(ctx)['drop_percent']==15


def test_search_denial_does_not_block_saving_preferences(tmp_path):
    from cosmos.core import permissions,agents
    from cosmos.core.registry import Registry
    from cosmos.core.personas import Persona
    from cosmos.core.orchestrator import Orchestrator
    ctx=context(tmp_path);p=ShoppingPlugin();reg=Registry();reg.register(p);agents.set_enabled(p.name,True)
    engine=SimpleNamespace(registry=reg,persona=Persona(),session=SimpleNamespace(user_id=ctx.user_id))
    permissions.set_state('shopping.search','deny')
    try:
        reply=Orchestrator.dispatch(engine,p.name,ctx,dict(action='settings',preferences=dict(price_checks=False,check_hours=24,drop_percent=10)))
        assert 'saved' in reply and not _preferences(ctx)['price_checks'] and not ctx.calls
    finally:permissions.set_state('shopping.search','default')


def test_pausing_during_search_prevents_a_late_alert(tmp_path,monkeypatch):
    ctx=context(tmp_path);p=ShoppingPlugin();notices=[];ctx.notice=lambda *a,**k:notices.append(a)
    def find(*args):
        save(ctx,price_checks=False)
        return [Candidate('Headphones',80,'USD')]
    monkeypatch.setattr(p,'_find',find)
    row=dict(watching=dict(title='Headphones',price=100,currency='USD'),query='Headphones',last_alert='',wish_id='fixture')
    p._check_one(ctx,row)
    assert not notices
