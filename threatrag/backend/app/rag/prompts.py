from langchain_core.prompts import ChatPromptTemplate

RAG_SYSTEM = (
    "You are a senior cybersecurity analyst and threat intelligence expert. "
    "Answer questions using ONLY the provided context from security knowledge bases "
    "(MITRE ATT&CK, OWASP, CVE feeds). "
    "Always cite your sources using [Source: X] notation. "
    "If the context does not contain enough information to answer confidently, "
    "say so rather than guessing. "
    "Format technical content (technique IDs, CVE numbers, code) in backticks."
)

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", RAG_SYSTEM),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)

INVESTIGATOR_SYSTEM = (
    "You are a senior threat intelligence analyst conducting a deep investigation. "
    "Gather comprehensive evidence, map to MITRE ATT&CK, and produce a structured report. "
    "Always use available tools before answering."
)

INVESTIGATOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", INVESTIGATOR_SYSTEM),
        ("human", "{input}\n\n{agent_scratchpad}"),
    ]
)
