"""Real Redis: expiry, counters shared between workers, chat history that survives a restart."""
import asyncio
import uuid
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent import session as session_mod
from app.core.state import RedisState
from tests.integration.conftest import REDIS_URL, require

pytestmark = pytest.mark.integration


@pytest.fixture
async def redis_state():
    require(REDIS_URL, 6379, "Redis")
    state = RedisState(REDIS_URL)
    yield state
    await state.close()


async def test_set_get_delete_and_expiry(redis_state):
    key = f"it:{uuid.uuid4().hex}"
    await redis_state.set(key, "v", ttl_s=1)
    assert await redis_state.get(key) == "v"
    await asyncio.sleep(1.3)
    assert await redis_state.get(key) is None
    await redis_state.set(key, "w")
    await redis_state.delete(key)
    assert await redis_state.get(key) is None


async def test_counter_is_shared_between_two_workers(redis_state):
    key, other_worker = f"it:rl:{uuid.uuid4().hex}", RedisState(REDIS_URL)
    try:
        assert [await redis_state.incr(key, 30), await other_worker.incr(key, 30), await redis_state.incr(key, 30)] == [1, 2, 3]
        assert 0 < await redis_state._client.ttl("threatrag:" + key) <= 30
    finally:
        await redis_state.delete(key)
        await other_worker.close()


async def test_chat_history_survives_a_new_process(redis_state):
    session_id = uuid.uuid4().hex
    with patch.object(session_mod, "get_state", return_value=redis_state):
        await session_mod.SessionHistory("alice", session_id).save([HumanMessage(content="q"), AIMessage(content="a")])
        restored = await session_mod.SessionHistory("alice", session_id).load()   # nothing shared but Redis
        assert [(type(m).__name__, m.content) for m in restored] == [("HumanMessage", "q"), ("AIMessage", "a")]
        assert await session_mod.SessionHistory("bob", session_id).load() == []
        await session_mod.SessionHistory("alice", session_id).clear()
        assert await session_mod.SessionHistory("alice", session_id).load() == []
