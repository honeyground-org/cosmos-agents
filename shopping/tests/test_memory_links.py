"""기억이 **엔티티를 가리키는가** — 쇼핑 쪽 배선.

코스모스의 규약은 *"기억은 자기가 말하는 엔티티를 가리킨다"* 이고(코어의
`tests/test_memory_links.py`가 지킨다), 여기서는 **쇼핑이 그 규약을 지키는지**를 잰다.
쇼핑이 마켓으로 나오면서 코어에서 이리로 옮겨 왔다 — 코어의 그물이 외부 에이전트에
매여 있으면, 그 에이전트를 안 깐 사람의 CI가 빨개진다.
"""
from __future__ import annotations

import pytest

from cosmos.contracts.memory import MEMORY_ENTITIES_KEY, linked_entities
from cosmos.runtime.memory_lite.provider import LiteMemoryProvider

USER = "u1"


@pytest.fixture()
def brain(tmp_path):
    return LiteMemoryProvider(tmp_path / "brain")


def test_a_shopping_search_points_at_the_intent_and_the_products(brain):
    """★*"이어폰"* 으로 검색했을 때 상품명만 적힌 기억까지 닿아야 한다★"""
    from shopping_core import Candidate, remember_search
    wish_id = remember_search(brain, USER, "무선 이어폰", [
        Candidate(title="소니 WF-1000XM5", price=289000, seen_at="2026-08-04T10:00:00"),
        Candidate(title="젠하이저 모멘텀", price=254000, seen_at="2026-08-04T10:00:00")])

    item = brain.recent(USER, k=5, kinds=["shopping"])[0]
    links = set(linked_entities(item.meta))
    assert wish_id in links, "의도를 가리키지 않습니다"
    # ★후보까지 가리켜야 한다★ 의도만 가리키면 상품명으로 들어온 질의가 못 닿는다
    products = {e.id: e.name for e in brain.find_entities(USER, kind="product")}
    assert products, "★측정 무효★ 상품 노드가 안 생겼습니다"
    missing = {name for pid, name in products.items() if pid not in links}
    assert not missing, f"후보를 가리키지 않습니다: {missing}"


