from __future__ import annotations

from typing import Literal

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from typing_extensions import TypedDict

from app.agent.tools import build_tools
from app.api.deps import get_store
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import SourceDoc
from app.rag.embedder import get_embedder

log = get_logger(__name__)


class InvestigationState(TypedDict):
    ioc: str
    ioc_type: Literal["ip", "hash", "domain", "cve", "technique"]
    researcher_output: str
    critic_feedback: str
    final_report: str
    sources: list[SourceDoc]
    tool_calls: list[dict]
    iteration: int
    status: Literal["researching", "critiquing", "reporting", "done", "error"]


class InvestigationRequest(BaseModel):
    ioc: str
    ioc_type: Literal["ip", "hash", "domain", "cve", "technique"]
    session_id: str | None = None


class RagasScores(BaseModel):
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    context_recall: float | None = None
    overall: float = 0.0


class InvestigationReport(BaseModel):
    ioc: str
    ioc_type: str
    final_report: str
    sources: list[SourceDoc] = []
    tool_calls: list[dict] = []
    ragas_scores: RagasScores | None = None


def _get_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.llm_model,
        openai_api_key=s.kimchi_api_key,  # type: ignore[arg-type]
        openai_api_base=s.kimchi_base_url,
    )


async def researcher_node(state: InvestigationState) -> InvestigationState:
    llm = _get_llm()
    store = get_store()
    embedder = get_embedder()
    tools = build_tools(store, embedder)
    llm_with_tools = llm.bind_tools(tools)

    prompt = (
        f"You are a threat intelligence researcher. IOC: {state['ioc_type']} = {state['ioc']}\n"
        "Gather comprehensive intelligence. Search the KB first, then CVE lookup, then web.\n"
        "Produce sections: IOC Overview, Technical Analysis, MITRE ATT&CK Mapping, Related Threats, Raw Evidence."
    )
    if state.get("critic_feedback") and state["critic_feedback"] != "APPROVED":
        prompt += f"\n\nPrevious gaps to address: {state['critic_feedback']}"

    response = await llm_with_tools.ainvoke(prompt)
    return {**state, "researcher_output": str(response.content), "status": "critiquing"}


async def critic_node(state: InvestigationState) -> InvestigationState:
    llm = _get_llm()
    prompt = (
        "You are a critical security reviewer. Review this research report and identify gaps.\n"
        "If thorough and accurate, respond with exactly: APPROVED\n"
        "Otherwise respond with: NEEDS_REVISION: <gap1> | <gap2> | ...\n\n"
        f"Research:\n{state['researcher_output'][:3000]}"
    )
    response = await llm.ainvoke(prompt)
    feedback = str(response.content).strip()
    new_iteration = state.get("iteration", 0) + 1

    if feedback.startswith("APPROVED") or new_iteration >= 2:
        return {**state, "critic_feedback": feedback, "iteration": new_iteration, "status": "reporting"}
    return {**state, "critic_feedback": feedback, "iteration": new_iteration, "status": "researching"}


async def reporter_node(state: InvestigationState) -> InvestigationState:
    llm = _get_llm()
    prompt = (
        f"Write a professional threat intelligence report for: {state['ioc']}\n"
        "Format:\n# Threat Intelligence Report: {ioc}\n"
        "## Executive Summary\n## Technical Analysis\n"
        "## MITRE ATT&CK Coverage (table: Tactic | Technique | Evidence)\n"
        "## Indicators of Compromise\n## Recommended Actions\n## References\n\n"
        f"Research data:\n{state['researcher_output'][:4000]}"
    )
    response = await llm.ainvoke(prompt)
    return {**state, "final_report": str(response.content), "status": "done"}


def _route_after_critic(state: InvestigationState) -> str:
    return "reporter" if state["status"] == "reporting" else "researcher"


def build_graph():
    g = StateGraph(InvestigationState)
    g.add_node("researcher", researcher_node)
    g.add_node("critic", critic_node)
    g.add_node("reporter", reporter_node)
    g.set_entry_point("researcher")
    g.add_edge("researcher", "critic")
    g.add_conditional_edges("critic", _route_after_critic, {"reporter": "reporter", "researcher": "researcher"})
    g.add_edge("reporter", END)
    return g.compile()


_graph = build_graph()


async def run_investigation(request: InvestigationRequest) -> InvestigationReport:
    initial: InvestigationState = {
        "ioc": request.ioc, "ioc_type": request.ioc_type,  # type: ignore[typeddict-item]
        "researcher_output": "", "critic_feedback": "", "final_report": "",
        "sources": [], "tool_calls": [], "iteration": 0, "status": "researching",
    }
    result = await _graph.ainvoke(initial)
    return InvestigationReport(ioc=result["ioc"], ioc_type=result["ioc_type"], final_report=result["final_report"])
