# Phase 2 — Agentic Loop Specification

## Goal
ReAct agent with 3 tools. Conversation memory. Streaming SSE chat endpoint.

---

## Backend Features

### F2.1 — RAG Search Tool (backend/app/agent/tools.py)
- `ThreatRAGSearchTool(BaseTool)`
- Args: `query: str`, `doc_types: list[str] | None`
- Embeds query, searches Qdrant, returns formatted source string
- Injection defence: `sanitise_tool_input()` on all inputs

### F2.2 — NVD CVE Tool (backend/app/agent/tools.py)
- `NVDCVETool(BaseTool)`
- Args: `cve_id` validated `^CVE-\d{4}-\d{4,}$`
- GET NVD API, parse CVSS score + severity + description
- Exponential backoff on 429, graceful not-found message

### F2.3 — Web Search Tool (backend/app/agent/tools.py)
- `TavilySearchTool(BaseTool)`
- Wraps `TavilySearchResults`, prefixes query with "cybersecurity threat: "
- Returns url + title + content[:300] per result
- Graceful error if API key not set

### F2.4 — Input Sanitisation (backend/app/agent/tools.py)
- `sanitise_tool_input(text)`: truncate to 500 chars, strip injection markers
- Applied to all tool inputs before use
- `max_tool_calls=10` guard in agent loop

### F2.5 — ReAct Agent (backend/app/agent/react_agent.py)
- `ThreatIntelAgent` using `create_react_agent`
- `run(question)` → `AgentResponse`
- `stream(question)` → `AsyncIterator[AgentStreamEvent]`

### F2.6 — Session Manager (backend/app/agent/session.py)
- `SessionManager`: `{session_id: (agent, last_accessed)}`
- 30-minute TTL, 100 session limit
- Background eviction task

### F2.7 — Agent Schemas (backend/app/models/agent_schemas.py)
- `AgentThought`, `AgentToolCall`, `AgentToolResult`, `AgentChunk`, `AgentDone`, `AgentError`
- Discriminated union `AgentStreamEvent`
- `to_sse(event)` serialiser

### F2.8 — Chat Route (backend/app/api/routes/chat.py)
- `POST /api/v1/chat/stream` — SSE with session management
- `GET /api/v1/chat/history/{session_id}` — conversation history
- `DELETE /api/v1/chat/history/{session_id}` — clear session
- `POST /api/v1/chat/suggestions` — generate 3 follow-up questions

---

## Frontend Features

### F2.9 — ToolCallTimeline (web/src/components/ToolCallTimeline.tsx)
- Cards: tool icon, name badge, input (80 chars), result (150 chars)
- Spinner for in-flight tool calls
- Slide-in animation as cards arrive

### F2.10 — ConversationSidebar (web/src/components/ConversationSidebar.tsx)
- Fetch chat history via react-query
- Role icon + first 60 chars + timestamp per entry
- Clear history + Export as Markdown buttons

### F2.11 — SearchSuggestions (web/src/components/SearchSuggestions.tsx)
- 6 suggestion chips when input empty
- Auto-submit on click
- Follow-up suggestions after first message

### F2.12 — Upgraded Chat Page
- Parse new SSE event types
- Show thoughts as italic gray-500 lines
- `session_id` in sessionStorage
- "New conversation" button

---

## Acceptance Criteria (Phase 2 Done When:)
- [ ] Agent uses RAG tool then answers with MITRE reference
- [ ] CVE lookup returns CVSS score for CVE-2021-44228
- [ ] Session memory maintains context across 2 turns
- [ ] Tool call timeline renders in frontend
- [ ] Max tool calls guard prevents infinite loops
