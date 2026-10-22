"""Layout model for the ThreatRAG architecture diagram: groups, nodes, and animated flows.

Coordinates are in a 1280x800 logical canvas; the renderer scales them.
Gutters (empty channels between groups) keep flow lines from crossing boxes.
"""
from dataclasses import dataclass, field

W, H = 1280, 800
G12, G23, G34, G45 = 220, 470, 778, 1003  # vertical gutters between column groups
TOP, BOTTOM = 78, 540                     # horizontal gutters above / below the panels

Point = tuple[float, float]


@dataclass
class Node:
    key: str
    x: float
    y: float
    w: float
    h: float
    title: str
    sub: str = ""

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    def L(self) -> Point: return (self.x, self.cy)
    def R(self) -> Point: return (self.x + self.w, self.cy)
    def T(self) -> Point: return (self.cx, self.y)
    def B(self) -> Point: return (self.cx, self.y + self.h)


@dataclass
class Group:
    title: str
    x: float
    y: float
    w: float
    h: float


@dataclass
class Flow:
    title: str
    caption: str
    color: str
    path: list[Point]
    alert_at: Point | None = None          # point where a failure badge appears (fallback flow)
    alert_text: str = ""
    nodes: list[str] = field(default_factory=list)


GROUPS = [
    Group("ANALYST CONSOLE · React 18", 24, 96, 182, 430),
    Group("API EDGE · FastAPI", 236, 96, 220, 430),
    Group("AGENTS · LangGraph", 486, 96, 276, 430),
    Group("AGENT TOOLS", 792, 96, 196, 430),
    Group("DATA & MODELS", 1018, 96, 240, 430),
    Group("SOURCES", 24, 552, 182, 156),
]

_N = [
    Node("ui_chat", 38, 132, 154, 56, "Chat", "tool timeline · SSE"),
    Node("ui_inv", 38, 212, 154, 56, "Investigate", "live agent cards"),
    Node("ui_kb", 38, 292, 154, 56, "Knowledge base", "upload · stats"),
    Node("ui_an", 38, 372, 154, 56, "Analytics", "eval trends"),
    Node("auth", 250, 128, 192, 46, "X-API-Key guard", "CORS · IOC validation"),
    Node("r_query", 250, 192, 192, 44, "/query", "ThreatRAGChain"),
    Node("r_chat", 250, 250, 192, 44, "/chat", "session memory"),
    Node("r_inv", 250, 308, 192, 44, "/investigate", "investigation service"),
    Node("r_ingest", 250, 366, 192, 44, "/ingest", "MITRE · OWASP · PDF"),
    Node("r_eval", 250, 424, 192, 44, "/evaluate", "LLM-judge RAGAs"),
    Node("agent", 512, 128, 224, 56, "ReAct chat agent", "≤10 tool calls · 10 turns"),
    Node("research", 512, 236, 224, 56, "Researcher", "ReAct sub-agent"),
    Node("critic", 512, 332, 224, 56, "Critic", "APPROVED / NEEDS_REVISION"),
    Node("report", 512, 428, 224, 56, "Reporter", "streams markdown report"),
    Node("t_rag", 806, 150, 168, 50, "threat_rag_search", "MITRE · OWASP KB"),
    Node("t_nvd", 806, 236, 168, 50, "nvd_cve_lookup", "NVD CVE API 2.0"),
    Node("t_web", 806, 322, 168, 50, "web_search", "Tavily"),
    Node("qdrant", 1032, 128, 212, 52, "Qdrant", "961 vectors · cosine"),
    Node("ollama", 1032, 200, 212, 52, "Ollama", "nomic-embed-text · 768d"),
    Node("kimchi", 1032, 276, 212, 46, "Kimchi LLM", "primary"),
    Node("gemini", 1032, 330, 212, 46, "Gemini", "fallback on 402/429/5xx"),
    Node("pg", 1032, 410, 212, 56, "Postgres + pgvector", "reports · evaluations"),
    Node("s_mitre", 38, 584, 154, 34, "MITRE ATT&CK STIX"),
    Node("s_owasp", 38, 626, 154, 34, "OWASP LLM Top 10"),
    Node("s_pdf", 38, 668, 154, 34, "Custom threat PDFs"),
]
NODES = {n.key: n for n in _N}
n = NODES


def _hv(p: Point, x: float, q: Point) -> list[Point]:
    """Horizontal → vertical → horizontal elbow from p to q through gutter x."""
    return [p, (x, p[1]), (x, q[1]), q]


FLOWS = [
    Flow(
        "1 · Ingest",
        "MITRE STIX and OWASP PDFs are chunked with deterministic IDs, embedded by Ollama, stored in Qdrant.",
        "#f0b45a",
        [n["s_mitre"].R(), (G12, n["s_mitre"].cy), (G12, n["r_ingest"].cy), n["r_ingest"].L(),
         n["r_ingest"].R(), (G23, n["r_ingest"].cy), (G23, BOTTOM), (G45, BOTTOM), (G45, n["ollama"].cy),
         n["ollama"].L(), n["ollama"].T(), n["qdrant"].B()],
        nodes=["s_mitre", "r_ingest", "ollama", "qdrant"],
    ),
    Flow(
        "2 · Ask",
        "/query embeds the question, retrieves top-k from Qdrant, and the LLM streams a cited answer over SSE.",
        "#4fc0d0",
        [*_hv(n["ui_chat"].R(), G12, n["r_query"].L()),
         n["r_query"].R(), (G23, n["r_query"].cy), (G23, TOP), (G45, TOP), (G45, n["qdrant"].cy), n["qdrant"].L(),
         n["qdrant"].R(), (1268, n["qdrant"].cy), (1268, n["kimchi"].cy), n["kimchi"].R(),
         n["kimchi"].L(), (G45, n["kimchi"].cy), (G45, BOTTOM + 8), (G12 - 8, BOTTOM + 8),
         (G12 - 8, n["ui_chat"].cy), n["ui_chat"].R()],
        nodes=["ui_chat", "r_query", "qdrant", "kimchi"],
    ),
    Flow(
        "3 · Investigate",
        "Researcher calls tools, the Critic sends gaps back once, the Reporter streams; report + embedding saved to pgvector.",
        "#5fd39a",
        [*_hv(n["ui_inv"].R(), G12, n["r_inv"].L()),
         n["r_inv"].R(), (G23, n["r_inv"].cy), (G23, n["research"].cy), n["research"].L(),
         n["research"].R(), (G34, n["research"].cy), (G34, n["t_nvd"].cy), n["t_nvd"].L(),
         (G34, n["t_nvd"].cy), (G34, n["research"].cy), n["research"].R(),
         n["research"].B(), n["critic"].T(),
         n["critic"].L(), (500, n["critic"].cy), (500, n["research"].cy), n["research"].L(),
         n["research"].B(), n["critic"].T(), n["critic"].B(), n["report"].T(),
         n["report"].R(), (G34, n["report"].cy), (G34, BOTTOM), (G45, BOTTOM), (G45, n["pg"].cy), n["pg"].L(),
         (G45, n["pg"].cy), (G45, BOTTOM + 8), (G12 - 8, BOTTOM + 8), (G12 - 8, n["ui_inv"].cy), n["ui_inv"].R()],
        nodes=["ui_inv", "r_inv", "research", "t_nvd", "critic", "report", "pg"],
    ),
    Flow(
        "4 · LLM fallback",
        "Kimchi returns 402 (credits exhausted), so the same call is replayed on Gemini, tools included. No user-visible error.",
        "#b3a6f0",
        [*_hv(n["ui_chat"].R(), G12, n["r_chat"].L()),
         n["r_chat"].R(), (G23, n["r_chat"].cy), (G23, n["agent"].cy), n["agent"].L(),
         n["agent"].R(), (G34, n["agent"].cy), (G34, TOP), (G45, TOP), (G45, n["kimchi"].cy), n["kimchi"].L(),
         (G45 + 14, n["kimchi"].cy), (G45 + 14, n["gemini"].cy), n["gemini"].L(),
         (G45, n["gemini"].cy), (G45, BOTTOM + 8), (G12 - 8, BOTTOM + 8), (G12 - 8, n["ui_chat"].cy), n["ui_chat"].R()],
        alert_at=n["kimchi"].L(),
        alert_text="402",
        nodes=["ui_chat", "r_chat", "agent", "kimchi", "gemini"],
    ),
]
