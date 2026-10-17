"""Researcher / Critic / Reporter node implementations for the investigation graph."""
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.prebuilt import create_react_agent

from app.agent import investigation_prompts as P
from app.agent.investigation_models import InvestigationState, ToolCallRecord
from app.agent.tools import MAX_TOOL_CALLS, build_tools
from app.api.deps import get_store
from app.core.llm import get_llm
from app.core.logging import get_logger
from app.models.schemas import SourceDoc
from app.rag.chain import point_to_source
from app.rag.embedder import get_embedder

log = get_logger(__name__)
MAX_RESEARCH_ITERATIONS = 2


def _extract_tool_calls(messages: list[BaseMessage]) -> list[ToolCallRecord]:
    outputs = {m.tool_call_id: str(m.content) for m in messages if isinstance(m, ToolMessage)}
    return [
        ToolCallRecord(name=tc["name"], input=str(tc["args"])[:200], output=outputs.get(tc["id"] or "", "")[:300])
        for m in messages if isinstance(m, AIMessage)
        for tc in m.tool_calls
    ]


async def _kb_sources(ioc: str) -> list[SourceDoc]:
    """Deterministic KB retrieval so every report carries citations, even if the LLM skips the tool."""
    vector = await get_embedder().embed(ioc)
    hits = await get_store().search(vector, k=5)
    return [point_to_source(h) for h in hits]


async def researcher_node(state: InvestigationState) -> dict[str, Any]:
    tools = build_tools(get_store(), get_embedder())
    agent = create_react_agent(get_llm(), tools, prompt=SystemMessage(content=P.RESEARCHER_SYSTEM))
    task = P.RESEARCHER_TASK.format(ioc_type=state["ioc_type"], ioc=state["ioc"])
    feedback = state.get("critic_feedback", "")
    if feedback.startswith("NEEDS_REVISION"):
        task += P.RESEARCHER_GAPS.format(gaps=feedback.removeprefix("NEEDS_REVISION:").strip())

    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=task)]},
            config={"recursion_limit": 2 * MAX_TOOL_CALLS + 1},
        )
        messages: list[BaseMessage] = result["messages"]
        output = str(messages[-1].content)
    except GraphRecursionError:
        log.warning("researcher_tool_limit", ioc=state["ioc"])
        messages, output = [], "Research truncated: tool-call limit reached."

    sources = state.get("sources") or await _kb_sources(state["ioc"])
    return {
        "researcher_output": output,
        "tool_calls": [*state.get("tool_calls", []), *_extract_tool_calls(messages)],
        "sources": sources,
        "status": "critiquing",
    }


async def critic_node(state: InvestigationState) -> dict[str, Any]:
    prompt = P.CRITIC.format(
        ioc_type=state["ioc_type"], ioc=state["ioc"], research=state["researcher_output"][:6000]
    )
    response = await get_llm().ainvoke(prompt)
    feedback = str(response.content).strip()
    iteration = state.get("iteration", 0) + 1
    approved = feedback.upper().startswith("APPROVED")
    if not approved and not feedback.startswith("NEEDS_REVISION"):
        feedback = f"NEEDS_REVISION: {feedback[:500]}"
    done = approved or iteration >= MAX_RESEARCH_ITERATIONS
    return {
        "critic_feedback": "APPROVED" if approved else feedback,
        "iteration": iteration,
        "status": "reporting" if done else "researching",
    }


async def reporter_node(state: InvestigationState) -> dict[str, Any]:
    sources = "\n".join(f"- {s.source} ({s.doc_type}): {s.text[:120]}" for s in state.get("sources", []))
    evidence = "\n".join(f"- {t['name']}({t['input']}) → {t['output'][:200]}" for t in state.get("tool_calls", []))
    prompt = P.REPORTER.format(
        ioc=state["ioc"],
        feedback=state.get("critic_feedback", ""),
        research=f"{state['researcher_output'][:8000]}\n\nTool evidence:\n{evidence}",
        sources=sources or "none",
    )
    response = await get_llm(streaming=True).ainvoke(prompt)
    return {"final_report": str(response.content), "status": "done"}


def route_after_critic(state: InvestigationState) -> str:
    return "reporter" if state.get("status") == "reporting" else "researcher"
