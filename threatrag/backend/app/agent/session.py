import asyncio
from datetime import datetime, timedelta

from app.agent.react_agent import ThreatIntelAgent
from app.agent.tools import build_tools
from app.api.deps import get_store
from app.core.logging import get_logger
from app.rag.embedder import get_embedder

log = get_logger(__name__)
SESSION_TTL_MINUTES = 30
MAX_SESSIONS = 100


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, tuple[ThreatIntelAgent, datetime]] = {}
        self._lock = asyncio.Lock()
        self._eviction_task: asyncio.Task | None = None

    def start(self) -> None:
        self._eviction_task = asyncio.create_task(self._evict_loop())

    def stop(self) -> None:
        if self._eviction_task:
            self._eviction_task.cancel()

    async def _evict_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            await self._evict_expired()

    async def _evict_expired(self) -> None:
        cutoff = datetime.utcnow() - timedelta(minutes=SESSION_TTL_MINUTES)
        async with self._lock:
            expired = [sid for sid, (_, ts) in self._sessions.items() if ts < cutoff]
            for sid in expired:
                del self._sessions[sid]
            if expired:
                log.info("sessions_evicted", count=len(expired))

    async def get_or_create(self, session_id: str) -> ThreatIntelAgent:
        async with self._lock:
            if session_id in self._sessions:
                agent, _ = self._sessions[session_id]
                self._sessions[session_id] = (agent, datetime.utcnow())
                return agent

            if len(self._sessions) >= MAX_SESSIONS:
                oldest = min(self._sessions.items(), key=lambda x: x[1][1])
                del self._sessions[oldest[0]]

            store = get_store()
            embedder = get_embedder()
            tools = build_tools(store, embedder)
            agent = ThreatIntelAgent(tools=tools)
            self._sessions[session_id] = (agent, datetime.utcnow())
            log.info("session_created", session_id=session_id)
            return agent

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


session_manager = SessionManager()
