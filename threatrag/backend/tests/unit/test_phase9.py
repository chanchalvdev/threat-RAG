"""Shared state, identity, rate limiting, session ownership and STIX export (no network)."""
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
import stix2
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage, HumanMessage

os.environ.setdefault("KIMCHI_API_KEY", "test-key-for-unit-tests")

from app.agent.investigation_models import InvestigationReport  # noqa: E402
from app.agent.react_agent import ThreatIntelAgent  # noqa: E402
from app.agent.session import SessionHistory, SessionManager  # noqa: E402
from app.api import identity  # noqa: E402
from app.api.routes import investigate as investigate_routes  # noqa: E402
from app.core import state as state_mod  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.stix_export import build_bundle  # noqa: E402

SECRET = "unit-test-secret-of-sufficient-length-0123456789"


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def _token(sub: str, exp_in: int = 3600, secret: str = SECRET) -> dict[str, str]:
    token = jwt.encode({"sub": sub, "exp": int(time.time()) + exp_in}, secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def test_memory_state_expires_and_counts():
    store = state_mod.MemoryState()
    await store.set("a", "1")
    await store.set("gone", "x", ttl_s=1)
    with patch.object(state_mod.time, "monotonic", return_value=time.monotonic() + 5):
        assert await store.get("a") == "1" and await store.get("gone") is None
    assert [await store.incr("n", 60) for _ in range(3)] == [1, 2, 3]
    await store.delete("a")
    assert await store.get("a") is None


async def test_redis_state_prefixes_keys_and_sets_expiry_once():
    client = MagicMock(get=AsyncMock(return_value="v"), set=AsyncMock(), delete=AsyncMock(),
                       incr=AsyncMock(side_effect=[1, 2]), expire=AsyncMock(), aclose=AsyncMock())
    with patch("redis.asyncio.from_url", return_value=client):
        store = state_mod.RedisState("redis://x")
    assert await store.get("k") == "v"
    client.get.assert_awaited_once_with("threatrag:k")
    await store.set("k", "v", ttl_s=9)
    client.set.assert_awaited_once_with("threatrag:k", "v", ex=9)
    assert [await store.incr("n", 60), await store.incr("n", 60)] == [1, 2]
    client.expire.assert_awaited_once_with("threatrag:n", 60)
    await store.delete("k")
    await store.close()
    client.aclose.assert_awaited_once()


def test_get_state_picks_backend_from_settings():
    with patch.object(state_mod, "get_settings", return_value=_settings()):
        assert isinstance(state_mod.get_state(), state_mod.MemoryState)
    state_mod.get_state.cache_clear()
    with patch.object(state_mod, "get_settings", return_value=_settings(redis_url="redis://x")), \
            patch("redis.asyncio.from_url", return_value=MagicMock()):
        assert isinstance(state_mod.get_state(), state_mod.RedisState)


async def test_history_survives_a_new_agent_and_is_private_to_its_owner():
    manager = SessionManager()
    with patch("app.agent.session.build_tools", return_value=[]), patch("app.agent.session.get_retriever"):
        first = manager.get("alice", "s1")
        await first._remember("q1", "a1")
        restarted = SessionManager().get("alice", "s1")   # a different worker, or after a restart
        await restarted._recall()
        assert [m.content for m in restarted._messages] == ["q1", "a1"]
        assert manager.get("alice", "s1") is first
    assert await manager.history("bob", "s1") == []
    await manager.clear("alice", "s1")
    assert await manager.history("alice", "s1") == []


async def test_agent_without_history_store_keeps_memory_in_process():
    agent = ThreatIntelAgent(tools=[])
    await agent._remember("q", "a")
    await agent._recall()
    assert len(agent._messages) == 2


async def test_anonymous_when_no_secret_and_jwt_required_when_set():
    with patch.object(identity, "get_settings", return_value=_settings()):
        assert (await identity.current_identity(None)).sub == "anonymous"
    with patch.object(identity, "get_settings", return_value=_settings(jwt_secret=SECRET)):
        who = await identity.current_identity(_token("alice")["Authorization"])
        assert who.sub == "alice" and who.authenticated
        for bad in (None, "Basic abc", _token("alice", exp_in=-10)["Authorization"],
                    _token("alice", secret="another-secret-of-sufficient-length-9876543210")["Authorization"]):
            with pytest.raises(identity.HTTPException) as err:
                await identity.current_identity(bad)
            assert err.value.status_code == 401
        assert identity.mint_token("carol")
    with patch.object(identity, "get_settings", return_value=_settings()), pytest.raises(RuntimeError):
        identity.mint_token("carol")


async def test_one_identity_cannot_read_or_clear_anothers_session(client):
    await SessionHistory("alice", "s1").save([HumanMessage(content="secret question"), AIMessage(content="answer")])
    with patch.object(identity, "get_settings", return_value=_settings(jwt_secret=SECRET)):
        assert len((await client.get("/api/v1/chat/history/s1", headers=_token("alice"))).json()) == 2
        assert (await client.get("/api/v1/chat/history/s1", headers=_token("bob"))).json() == []
        await client.delete("/api/v1/chat/history/s1", headers=_token("bob"))
        assert len((await client.get("/api/v1/chat/history/s1", headers=_token("alice"))).json()) == 2
        assert (await client.get("/api/v1/chat/history/s1")).status_code == 401


async def test_rate_limit_returns_429_with_retry_after(client):
    with patch.object(identity, "get_settings", return_value=_settings(rate_limit_per_minute=3)):
        codes = [(await client.get("/api/v1/metrics")).status_code for _ in range(5)]
        last = await client.get("/api/v1/metrics")
    assert codes == [200, 200, 200, 429, 429] and int(last.headers["retry-after"]) > 0
    with patch.object(identity, "get_settings", return_value=_settings(rate_limit_per_minute=0)):
        assert (await client.get("/api/v1/metrics")).status_code == 200


NAMES = {"T1190": "Exploit Public-Facing Application", "T1059": "Command and Scripting Interpreter"}


@pytest.mark.parametrize("ioc,ioc_type,subject", [
    ("CVE-2021-44228", "cve", "vulnerability"), ("8.8.8.8", "ip", "indicator"), ("2001:4860:4860::8888", "ip", "indicator"),
    ("evil.example.com", "domain", "indicator"), ("d41d8cd98f00b204e9800998ecf8427e", "hash", "indicator"),
    ("T1190", "technique", None),
])
def test_stix_bundle_is_valid_and_links_cited_techniques(ioc, ioc_type, subject):
    report = InvestigationReport(ioc=ioc, ioc_type=ioc_type, report_id="r1", created_at="2026-10-16 20:11:09.123456+00",
                                 final_report="Exploited via T1190, then T1059. Also cites T9999.")
    bundle = build_bundle(report, NAMES)
    stix2.parse(json.dumps(bundle), allow_custom=False)   # raises on any spec violation
    kinds = [o["type"] for o in bundle["objects"]]
    assert kinds.count("attack-pattern") == 2             # T9999 is not in the corpus, so it is not exported
    assert (subject in kinds) if subject else ("relationship" not in kinds)
    assert kinds.count("relationship") == (2 if subject else 0)
    assert build_bundle(report, NAMES)["id"] == bundle["id"]  # deterministic


def test_stix_report_without_known_techniques_is_still_valid():
    report = InvestigationReport(ioc="T1190", ioc_type="technique", final_report="nothing cited")
    stix2.parse(json.dumps(build_bundle(report, {})), allow_custom=False)


async def test_stix_route_returns_downloadable_bundle(client):
    report = InvestigationReport(ioc="CVE-2021-44228", ioc_type="cve", final_report="T1190", report_id="r1")
    store = MagicMock(technique_names=AsyncMock(return_value=NAMES))
    with patch.object(investigate_routes, "get_report", new=AsyncMock(return_value=report)), \
            patch.object(investigate_routes, "get_store", return_value=store):
        r = await client.get("/api/v1/investigate/reports/r1/stix")
    assert r.status_code == 200 and r.json()["type"] == "bundle"
    assert "stix+json" in r.headers["content-type"] and "threatrag-r1.stix.json" in r.headers["content-disposition"]


async def test_readiness_is_ready_when_one_llm_provider_works_and_names_timeouts(httpx_mock):
    import httpx

    from app.services import readiness

    settings = _settings(gemini_api_key="g", gemini_base_url="http://gem", kimchi_api_key="k", kimchi_base_url="http://kim",
                         qdrant_url="http://q", qdrant_collection="c", embedding_provider="gemini", redis_url="redis://x")
    httpx_mock.add_response(url="http://q/collections/c", json={})
    httpx_mock.add_response(url="http://gem/chat/completions", json={})
    httpx_mock.add_response(url="http://kim/chat/completions", status_code=402)
    readiness._cache.update({"data": None, "expires": 0.0})
    with patch.object(readiness, "get_settings", return_value=settings), patch.object(readiness, "is_db_ready", return_value=True), \
            patch.object(readiness, "get_pool", return_value=MagicMock()), patch.object(readiness, "_probe_postgres", AsyncMock(return_value="ok")):
        result = await readiness.check_readiness()
    readiness._cache.update({"data": None, "expires": 0.0})
    assert result.status == "ready"
    assert result.checks == {"qdrant": "ok", "llm": "ok", "llm_fallback": "http_402", "postgres": "ok", "redis": "ok"}

    httpx_mock.add_exception(httpx.ReadTimeout(""), url="http://gem/chat/completions")
    assert await readiness._probe_llm("http://gem", "g", "m") == "error: ReadTimeout"
