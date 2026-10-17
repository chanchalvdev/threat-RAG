import asyncio
import re
from typing import Any, Type

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from app.core.logging import get_logger
from app.rag.embedder import BaseEmbedder
from app.rag.sanitiser import sanitise_tool_input
from app.rag.store import QdrantStore

log = get_logger(__name__)
MAX_TOOL_CALLS = 10
_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$")


class RAGSearchInput(BaseModel):
    query: str = Field(..., description="Search query for the threat intel knowledge base")
    doc_types: list[str] | None = Field(default=None, description="Optional filter: mitre_attack, owasp_llm, custom")


class ThreatRAGSearchTool(BaseTool):  # type: ignore[override]  # pydantic __replace__ stub quirk
    name: str = "threat_rag_search"
    description: str = (
        "Search the internal security knowledge base (MITRE ATT&CK, OWASP LLM Top 10, threat intel). "
        "Use this FIRST for any security question."
    )
    args_schema: Type[BaseModel] = RAGSearchInput

    model_config = ConfigDict(arbitrary_types_allowed=True)

    store: Any = Field(exclude=True)
    embedder: Any = Field(exclude=True)

    async def _arun(self, query: str, doc_types: list[str] | None = None) -> str:
        clean = sanitise_tool_input(query)
        vector = await self.embedder.embed(clean)
        hits = await self.store.search(vector, k=6, doc_types=doc_types)
        if not hits:
            return "No relevant documents found in knowledge base."
        return "\n---\n".join(
            f"[Source: {h.payload.get('source', '')}]\n{h.payload.get('text', '')}"
            for h in hits
        )

    def _run(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Use async only")


class CVEInput(BaseModel):
    cve_id: str = Field(..., description="CVE ID in format CVE-YYYY-NNNNN")


class NVDCVETool(BaseTool):  # type: ignore[override]  # pydantic __replace__ stub quirk
    name: str = "nvd_cve_lookup"
    description: str = "Look up CVE details from the NVD database. Use when a specific CVE ID is mentioned."
    args_schema: Type[BaseModel] = CVEInput

    async def _arun(self, cve_id: str) -> str:
        cve_id = sanitise_tool_input(cve_id)
        if not _CVE_RE.match(cve_id):
            return f"Invalid CVE ID format: {cve_id}"

        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
        for attempt in range(3):
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(url)
                if r.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if r.status_code == 404 or not r.json().get("vulnerabilities"):
                    return f"CVE {cve_id} not found in NVD."
                r.raise_for_status()
                return _parse_nvd(r.json(), cve_id)
        return "NVD API rate limit reached. Try again later."

    def _run(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Use async only")


def _parse_nvd(data: dict, cve_id: str) -> str:
    vuln = data["vulnerabilities"][0]["cve"]
    desc = next(
        (d["value"] for d in vuln.get("descriptions", []) if d["lang"] == "en"), "No description"
    )[:500]
    metrics = vuln.get("metrics", {})
    cvss_data = (
        metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {})
        or metrics.get("cvssMetricV2", [{}])[0].get("cvssData", {})
    )
    score = cvss_data.get("baseScore", "N/A")
    severity = cvss_data.get("baseSeverity", "N/A")
    configs = vuln.get("configurations", [])
    affected = [
        n.get("cpeMatch", [{}])[0].get("criteria", "")
        for node in configs[:1]
        for n in node.get("nodes", [])[:3]
    ]
    return (
        f"CVE ID: {cve_id}\nCVSS Score: {score}\nSeverity: {severity}\n"
        f"Description: {desc}\nAffected: {', '.join(affected[:3]) or 'See NVD for details'}"
    )


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query for web threat intelligence")


class TavilySearchTool(BaseTool):  # type: ignore[override]  # pydantic __replace__ stub quirk
    name: str = "web_search"
    description: str = (
        "Search the web for current threat intelligence, recent security news, "
        "or information not in the knowledge base. Use as a last resort."
    )
    args_schema: Type[BaseModel] = WebSearchInput

    async def _arun(self, query: str) -> str:
        from app.core.config import get_settings
        s = get_settings()
        if not s.tavily_api_key:
            return "Web search not available: TAVILY_API_KEY not configured."

        from langchain_community.tools.tavily_search import TavilySearchResults
        clean = sanitise_tool_input(f"cybersecurity threat: {query}")
        tool = TavilySearchResults(api_key=s.tavily_api_key, max_results=5)
        results = await tool.ainvoke({"query": clean})
        return "\n---\n".join(
            f"[{r.get('title', '')}] {r.get('url', '')}\n{r.get('content', '')[:300]}"
            for r in (results if isinstance(results, list) else [])
        )

    def _run(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError("Use async only")


def build_tools(store: QdrantStore, embedder: BaseEmbedder) -> list[BaseTool]:
    return [
        ThreatRAGSearchTool(store=store, embedder=embedder),
        NVDCVETool(),
        TavilySearchTool(),
    ]
