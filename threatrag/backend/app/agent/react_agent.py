from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.agent_schemas import (
    AgentChunk, AgentDone, AgentError, AgentThought, AgentToolCall,
    AgentToolResult, ToolCallData, to_sse,
)

log = get_logger(__name__)

SYSTEM_PROMPT = (
    "You are a senior threat intelligence analyst. Use available tools to answer "
    "security questions thoroughly. Search the knowledge base first (threat_rag_search), "
    "then look up specific CVEs (nvd_cve_lookup), and search the web only for recent info "
    "(web_search). Provide your final answer in structured markdown with sections: "
    "Summary, Technical Details, MITRE ATT&CK Mapping, Recommendations."
)


class AgentResponse(BaseModel):
    answer: str
    total_tokens: int = 0


def _build_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.llm_model,
        openai_api_key=s.kimchi_api_key,  # type: ignore[arg-type]
        openai_api_base=s.kimchi_base_url,
        streaming=True,
    )


class ThreatIntelAgent:
    def __init__(self, tools: list[BaseTool]):
        self._llm = _build_llm()
        self._tools = tools
        self._graph = create_react_agent(
            self._llm,
            tools,
            prompt=SystemMessage(content=SYSTEM_PROMPT),
        )
        self._history: list[dict[str, str]] = []

    async def run(self, question: str) -> AgentResponse:
        messages = [HumanMessage(content=question)]
        result = await self._graph.ainvoke({"messages": messages})
        answer = str(result["messages"][-1].content)
        self._history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        return AgentResponse(answer=answer)

    async def stream(self, question: str, session_id: str) -> AsyncIterator[str]:
        try:
            messages = [HumanMessage(content=question)]
            yield to_sse(AgentThought(data="Starting investigation..."))

            async for event in self._graph.astream_events(
                {"messages": messages}, version="v2"
            ):
                kind = event["event"]
                if kind == "on_tool_start":
                    yield to_sse(AgentToolCall(
                        data=ToolCallData(
                            name=event["name"],
                            input=str(event.get("data", {}).get("input", "")),
                            tool_use_id=event["run_id"],
                        )
                    ))
                elif kind == "on_tool_end":
                    yield to_sse(AgentToolResult(
                        data=str(event.get("data", {}).get("output", ""))[:500],
                        tool_use_id=event["run_id"],
                    ))
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield to_sse(AgentChunk(data=str(chunk.content)))

            yield to_sse(AgentDone(session_id=session_id))
        except Exception as exc:
            log.error("agent_stream_error", error=str(exc))
            yield to_sse(AgentError(data=str(exc)))

    def get_history(self) -> list[dict[str, str]]:
        return self._history

    def clear_history(self) -> None:
        self._history = []
