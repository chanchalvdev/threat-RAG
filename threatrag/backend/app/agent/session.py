"""Chat sessions: agents are cached per process, conversation history lives in shared state."""
import json

from langchain_core.messages import BaseMessage, messages_from_dict, messages_to_dict

from app.agent.react_agent import ThreatIntelAgent
from app.agent.tools import build_tools
from app.api.deps import get_retriever
from app.core.logging import get_logger
from app.core.state import get_state

log = get_logger(__name__)
SESSION_TTL_S = 30 * 60
MAX_CACHED_AGENTS = 100


class SessionHistory:
    """One conversation's messages, stored under its owner so identities cannot see each other's."""

    def __init__(self, owner: str, session_id: str):
        self.key = f"chat:{owner}:{session_id}"

    async def load(self) -> list[BaseMessage]:
        raw = await get_state().get(self.key)
        return messages_from_dict(json.loads(raw)) if raw else []

    async def save(self, messages: list[BaseMessage]) -> None:
        await get_state().set(self.key, json.dumps(messages_to_dict(messages)), ttl_s=SESSION_TTL_S)

    async def clear(self) -> None:
        await get_state().delete(self.key)


class SessionManager:
    def __init__(self) -> None:
        self._agents: dict[str, ThreatIntelAgent] = {}

    def get(self, owner: str, session_id: str) -> ThreatIntelAgent:
        """The agent for this owner's session. History is read from shared state on every turn,
        so any worker can serve the next message and a restart loses nothing."""
        history = SessionHistory(owner, session_id)
        agent = self._agents.get(history.key)
        if agent is None:
            if len(self._agents) >= MAX_CACHED_AGENTS:
                self._agents.pop(next(iter(self._agents)))  # oldest cached graph; its history stays in state
            agent = ThreatIntelAgent(tools=build_tools(get_retriever()), history=history)
            self._agents[history.key] = agent
            log.info("session_agent_created", session_id=session_id)
        return agent

    async def history(self, owner: str, session_id: str) -> list[BaseMessage]:
        return await SessionHistory(owner, session_id).load()

    async def clear(self, owner: str, session_id: str) -> None:
        self._agents.pop(f"chat:{owner}:{session_id}", None)
        await SessionHistory(owner, session_id).clear()


session_manager = SessionManager()
