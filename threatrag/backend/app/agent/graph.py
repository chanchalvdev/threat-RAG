"""LangGraph assembly for Researcher → Critic → (Researcher | Reporter) and its event stream."""
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.agent.investigation_models import (
    InvestigationReport,
    InvestigationRequest,
    InvestigationState,
    ReportSummary,
)
from app.agent.nodes import critic_node, reporter_node, researcher_node, route_after_critic
from app.core.logging import get_logger

__all__ = ["InvestigationReport", "InvestigationRequest", "ReportSummary", "run_investigation", "stream_investigation"]

log = get_logger(__name__)
NODES = ("researcher", "critic", "reporter")
GRAPH_CONFIG: RunnableConfig = {"recursion_limit": 12}


def build_graph() -> Any:
    g = StateGraph(InvestigationState)
    g.add_node("researcher", researcher_node)
    g.add_node("critic", critic_node)
    g.add_node("reporter", reporter_node)
    g.set_entry_point("researcher")
    g.add_edge("researcher", "critic")
    g.add_conditional_edges("critic", route_after_critic, {"reporter": "reporter", "researcher": "researcher"})
    g.add_edge("reporter", END)
    return g.compile()


_graph = build_graph()


def _initial_state(req: InvestigationRequest) -> InvestigationState:
    return {
        "ioc": req.ioc, "ioc_type": req.ioc_type, "researcher_output": "", "critic_feedback": "",
        "final_report": "", "sources": [], "tool_calls": [], "iteration": 0, "status": "researching",
    }


def _to_report(state: InvestigationState) -> InvestigationReport:
    return InvestigationReport(
        ioc=state["ioc"],
        ioc_type=state["ioc_type"],
        final_report=state.get("final_report", ""),
        sources=state.get("sources", []),
        tool_calls=state.get("tool_calls", []),
        critic_feedback=state.get("critic_feedback", ""),
        iterations=state.get("iteration", 1),
    )


async def run_investigation(req: InvestigationRequest) -> InvestigationReport:
    result = await _graph.ainvoke(_initial_state(req), config=GRAPH_CONFIG)
    return _to_report(result)


def _summary(node: str, update: dict[str, Any]) -> str:
    if node == "researcher":
        return f"{len(update.get('tool_calls', []))} tool calls · {len(update.get('researcher_output', ''))} chars"
    if node == "critic":
        return str(update.get("critic_feedback", ""))[:200]
    return f"{len(update.get('final_report', ''))} char report"


async def stream_investigation(req: InvestigationRequest) -> AsyncIterator[dict[str, Any]]:
    """Map LangGraph v2 events to UI events. Last event is {'type': 'complete', 'report': ...}."""
    state: dict[str, Any] = dict(_initial_state(req))
    researcher_runs = 0
    async for ev in _graph.astream_events(state, version="v2", config=GRAPH_CONFIG):
        kind, name = ev["event"], ev.get("name", "")
        node = ev.get("metadata", {}).get("langgraph_node")
        if kind == "on_chain_start" and name in NODES and node == name:
            researcher_runs += name == "researcher"
            yield {"type": "node_start", "node": name, "iteration": researcher_runs}
        elif kind == "on_chain_end" and name in NODES and node == name:
            update = ev["data"].get("output") or {}
            if isinstance(update, dict):
                state.update(update)
                yield {"type": "node_done", "node": name, "summary": _summary(name, update)}
                if name == "critic":
                    target = route_after_critic(state)  # type: ignore[arg-type]
                    yield {"type": "routing", "from": "critic", "to": target, "reason": state["critic_feedback"][:200]}
        elif kind == "on_tool_start":
            yield {"type": "tool_call", "node": "researcher", "name": name, "input": str(ev["data"].get("input", ""))[:200]}
        elif kind == "on_chat_model_stream" and node == "reporter":
            chunk = ev["data"].get("chunk")
            if chunk is not None and chunk.content:
                yield {"type": "report_chunk", "data": str(chunk.content)}
    yield {"type": "complete", "report": _to_report(state)}  # type: ignore[arg-type]
