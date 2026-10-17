import asyncio
from collections.abc import AsyncIterator

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from app.agent.tools import MAX_TOOL_CALLS
from app.core.llm import get_llm
from app.core.logging import get_logger
from app.models.agent_schemas import (
    AgentChunk, AgentDone, AgentError, AgentThought, AgentToolCall,
    AgentToolResult, ToolCallData, to_sse,
)

log = get_logger(__name__)
MAX_HISTORY_MESSAGES = 20  # 10 user/assistant turns
_RUN_CONFIG: RunnableConfig = {"recursion_limit": 2 * MAX_TOOL_CALLS + 1}

SYSTEM_PROMPT = (
    "You are a senior threat intelligence analyst. Use available tools to answer "
    "security questions thoroughly. Search the knowledge base first (threat_rag_search), "
    "then look up specific CVEs (nvd_cve_lookup), and search the web only for recent info "
    "(web_search). Use earlier turns of the conversation to resolve references like 'it' or "
    "'that CVE'. Provide your final answer in structured markdown with sections: "
    "Summary, Technical Details, MITRE ATT&CK Mapping, Recommendations."
)


class AgentResponse(BaseModel):
    answer: str
    total_tokens: int = 0


class ThreatIntelAgent:
    """ReAct agent with a rolling 10-turn conversation memory. One instance per session."""

    def __init__(self, tools: list[BaseTool]):
        self._tools = tools
        self._graph = create_react_agent(
            get_llm(streaming=True), tools, prompt=SystemMessage(content=SYSTEM_PROMPT)
        )
        self._messages: list[BaseMessage] = []
        self._lock = asyncio.Lock()  # serialise turns within a session

    def _input(self, question: str) -> dict[str, list[BaseMessage]]:
        return {"messages": [*self._messages[-MAX_HISTORY_MESSAGES:], HumanMessage(content=question)]}

    def _remember(self, question: str, answer: str) -> None:
        self._messages.extend([HumanMessage(content=question), AIMessage(content=answer)])
        self._messages = self._messages[-MAX_HISTORY_MESSAGES:]

    async def run(self, question: str) -> AgentResponse:
        async with self._lock:
            result = await self._graph.ainvoke(self._input(question), config=_RUN_CONFIG)
            answer = str(result["messages"][-1].content)
            self._remember(question, answer)
            return AgentResponse(answer=answer)

    async def stream(self, question: str, session_id: str) -> AsyncIterator[str]:
        async with self._lock:
            answer = ""  # text of the latest model turn = final answer
            try:
                yield to_sse(AgentThought(data="Starting investigation..."))
                async for event in self._graph.astream_events(
                    self._input(question), version="v2", config=_RUN_CONFIG
                ):
                    kind = event["event"]
                    data = event.get("data", {})
                    if kind == "on_tool_start":
                        answer = ""
                        yield to_sse(AgentToolCall(data=ToolCallData(
                            name=event["name"], input=str(data.get("input", "")), tool_use_id=event["run_id"],
                        )))
                    elif kind == "on_tool_end":
                        output = data.get("output", "")
                        text = getattr(output, "content", output)
                        yield to_sse(AgentToolResult(data=str(text)[:500], tool_use_id=event["run_id"]))
                    elif kind == "on_chat_model_stream":
                        chunk = data.get("chunk")
                        if chunk is not None and chunk.content:
                            answer += str(chunk.content)
                            yield to_sse(AgentChunk(data=str(chunk.content)))
                self._remember(question, answer)
                yield to_sse(AgentDone(session_id=session_id))
            except GraphRecursionError:
                yield to_sse(AgentError(data=f"Stopped: exceeded {MAX_TOOL_CALLS} tool calls."))
            except Exception as exc:
                log.error("agent_stream_error", error=str(exc))
                yield to_sse(AgentError(data=str(exc)))

    def get_history(self) -> list[dict[str, str]]:
        return [
            {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": str(m.content)}
            for m in self._messages
        ]

    def clear_history(self) -> None:
        self._messages = []
