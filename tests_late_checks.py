"""Slow supplier results must not outlive the user's permission or purchase decision."""
from types import SimpleNamespace
import pytest
import shopping_scout as shopping
import flights_scout as flights
from cosmos.core import permissions

@pytest.mark.parametrize('module,kind',[(shopping,'shopping'),(flights,'flights')])
@pytest.mark.parametrize('change',['memory','network','finished'])
def test_late_check_cannot_write_after_revocation_or_finished_purchase(monkeypatch,module,kind,change):
    plugin=module.ShoppingPlugin() if kind=='shopping' else module.FlightsPlugin()
    ctx=SimpleNamespace(user_id='late-check',brain=object())
    row={'wish_id':'wish','query':'headphones','watching':{'title':'headphones','price':100,'currency':'USD'},
         'origin':'ICN','destination':'Tokyo','depart':'2027-01-10'}
    blocked=set();active=[row]
    monkeypatch.setattr(permissions,'effective_blocked',lambda:blocked)
    monkeypatch.setattr(module,'watchlist',lambda *a:active)
    monkeypatch.setattr(module,'remember_check',lambda *a,**kw:pytest.fail('stale check wrote memory'))
    if kind=='shopping':
        monkeypatch.setattr(module,'_preferences',lambda ctx:{'price_checks':True})
    def find(*a):
        if change=='finished':active.clear()
        else:blocked.add(change)
        return [] if kind=='shopping' else ([],{})
    monkeypatch.setattr(plugin,'_find',find)
    plugin._check_one(ctx,row)
