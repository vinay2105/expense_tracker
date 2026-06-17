# Spendly — Conversational Expense Tracker powered by MCP + LangGraph


> **Talk to your expenses.** Spendly lets you add, search, analyze, and delete expenses through a natural language AI chatbot — powered by a LangGraph ReAct agent, an LLM, and a JWT-authenticated FastMCP server.

---

## What Makes This Project Different

Most expense trackers give you forms and dashboards. Spendly gives you a conversation.

The core idea: instead of clicking through a UI, you just ask:

> *"How much did I spend on food this month?"*
> *"Add ₹450 for Swiggy, Food category, paid by UPI"*
> *"Delete my last travel expense"*

Under the hood, a **LangGraph ReAct agent** figures out which tool to call, calls it through an **MCP server**, and returns a natural language answer — all while keeping your data completely isolated from other users via JWT.

---

## The AI Stack (Core of the Project)

```
User Message
     │
     ▼
LangGraph ReAct Agent  ←── LLM
     │
     │  "I need to call list_my_recent_expenses"
     ▼
MultiServerMCPClient
     │  Authorization: Bearer <user JWT>
     ▼
FastMCP Server  (/mcp)
     │  JWTVerifier → TokenClaim("sub") → user_id
     ▼
SQLAlchemy CRUD
     │
     ▼
PostgreSQL Database
     │
     ▼
Tool Result → Agent → LLM → Final Response
```

---

## How the Chatbot Works — Step by Step

### 1. User sends a message

```bash
POST /chat
Authorization: Bearer eyJhbGci...
{"message": "What did I spend on food this month?"}
```

### 2. FastAPI extracts the JWT and calls `build_agent(access_token)`

```python
# chatbot.py
async def build_agent(access_token: str):
    client = MultiServerMCPClient({
        "expense_tracker": {
            "transport": "streamable_http",
            "url": "http://localhost:8000/mcp",
            "headers": {"Authorization": f"Bearer {access_token}"}
        }
    })
    tools = await client.get_tools()   # discovers MCP tools automatically
    agent = create_react_agent(llm, tools, prompt=systemprompt, checkpointer=memory)
    return agent
```

### 3. LangGraph runs the ReAct loop

```
Thought:  User wants food spending for this month
Action:   get_my_expense_summary
Result:   {month_total: 4250, top_category: {name: "Food & Dining", total: 1800}}
Thought:  I have the data, I can answer now
Answer:   "You spent ₹1,800 on Food & Dining this month — 42% of your ₹4,250 total."
```

### 4. The MCP server receives the tool call with the JWT

```python
# mcp_server.py
@mcp.tool(name="get_my_expense_summary")
def get_my_expense_summary(subject: str = TokenClaim("sub")) -> dict:
    user_id = trusted_user_id(subject)   # extracted from token, NOT from agent input
    with SessionLocal() as db:
        return get_dashboard_statistics(db, user_id)
```

**Key point:** The agent never passes a `user_id`. It comes from the JWT `sub` claim — the LLM physically cannot access another user's data even if it tried.

---

## MCP Server — Deep Dive

The MCP server is the bridge between the AI agent and the database. It exposes 6 tools that the LLM can discover and call.

### Why MCP instead of direct function calls?

| Direct Function Call | MCP Tool |
|---|---|
| Hardcoded in agent code | Discovered dynamically at runtime |
| Agent knows implementation | Agent only sees name + description + schema |
| No standard protocol | Standard protocol — any MCP-compatible LLM can use it |
| Auth is manual | Auth is enforced by the server via JWTVerifier |

### Authentication inside MCP

```python
mcp = FastMCP(
    name="Spendly Expense MCP",
    auth=JWTVerifier(public_key=SECRET_KEY, algorithm="HS256"),
)
```

Every request to `/mcp` must carry a valid Bearer token. FastMCP verifies it before any tool runs. The verified token's `sub` claim is then injected into every tool function via `TokenClaim("sub")` — no separate user lookup needed.

```python
# This is how user identity flows into every tool
def list_my_recent_expenses(
    limit: int = 10,
    subject: str = TokenClaim("sub"),   # ← injected from verified JWT, not from LLM
) -> list[dict]:
    user_id = int(subject)
    ...
```

### The 6 MCP Tools

#### `get_my_expense_summary`
Returns month total, all-time total, transaction count, daily average, top category, and full category breakdown.

```json
{
  "month_total": "4250.00",
  "total_expenses": "18500.00",
  "transaction_count": 42,
  "daily_average": "303.57",
  "month_name": "June",
  "top_category": { "name": "Food & Dining", "total": "1800.00", "percentage": 42.35 },
  "categories": [...]
}
```

#### `list_my_recent_expenses`
Returns last N expenses (1–100), ordered by date descending.

```json
[
  { "id": 47, "amount": "320.00", "category": "Food & Dining",
    "description": "Swiggy dinner", "payment_method": "UPI", "expense_date": "2026-06-17" }
]
```

#### `search_my_expenses`
Filters by category (exact match), date range, and description (case-insensitive `ILIKE`). All filters optional.

```python
search_expenses(db, user_id, category="Travel", start_date=date(2026,6,1), description="flight")
```

#### `get_my_category_breakdown`
Category-level totals and percentages for the current month only.

#### `add_my_expense`
Creates a new expense row. The agent uses this only when the user clearly asks to record something.

```python
# Agent call
add_my_expense(amount=450, category="Food & Dining", description="Swiggy", payment_method="UPI")
```

#### `delete_my_expense`
Deletes by `expense_id`. The tool description explicitly tells the agent to **confirm with the user before calling this**. The system prompt enforces the same rule.

```python
@mcp.tool(
    name="delete_my_expense",
    description="Delete one expense. The agent MUST obtain explicit user confirmation before calling this."
)
def delete_my_expense(expense_id: int, subject: str = TokenClaim("sub")) -> dict:
    user_id = trusted_user_id(subject)
    with SessionLocal() as db:
        if not delete_expense(db, user_id, expense_id):
            raise ToolError("Expense not found.")
    return {"deleted": True, "expense_id": expense_id}
```

---

## LangGraph Agent — Deep Dive

### Why LangGraph + ReAct?

- **ReAct (Reason + Act)** — the agent reasons about what tool to call, calls it, observes the result, and reasons again. This loop continues until it has enough information to answer.
- **LangGraph** provides the graph execution engine, checkpointing, and async support.
- **Alternative considered:** plain function calling — but ReAct handles multi-step reasoning better (e.g., "search then summarize" in one turn).

### Agent Configuration

```python
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY,
    temperature=0,          # deterministic — no hallucinated numbers
)

memory = InMemorySaver()    # per-user conversation history

agent = create_react_agent(
    llm,
    tools,                  # loaded from MCP at runtime
    prompt=systemprompt,
    checkpointer=memory,    # enables multi-turn memory
)
```

### Memory & Thread Isolation

```python
config = {"configurable": {"thread_id": thread_id}}  # thread_id = user's JWT sub
response = await agent.ainvoke({"messages": [...]}, config=config)
```

`thread_id` is set to the user's ID from the JWT. This means:
- Each user has their own isolated conversation history
- The agent remembers context within a session ("delete the one I just added")
- Different users' threads never mix

### The System Prompt — Why It Matters

```
You are Spendly AI, an expense tracking assistant.

Rules:
1. Only answer questions related to expense tracking.
2. Always use tools — never invent expenses, totals, or categories.
3. If asked something unrelated, respond: "I am an expense tracking assistant..."
4. Before deleting any expense, obtain explicit confirmation from the user.
5. Keep responses short and focused.
```

This prompt is the last line of defence against:
- **Hallucination** — rule 2 forces tool use instead of making up numbers
- **Scope creep** — rule 1 blocks general questions (coding, math, history)
- **Accidental deletes** — rule 4 enforces a confirmation gate before destructive actions

---

## Full Conversation Flow

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI /chat
    participant Agent as LangGraph ReAct
    participant LLM as LLM
    participant MCP as FastMCP /mcp
    participant DB as PostgreSQL

    User->>API: POST /chat {"message": "how much did I spend this month?"}
    API->>Agent: build_agent(access_token)
    Agent->>MCP: GET /mcp/tools  (Bearer JWT)
    MCP-->>Agent: [get_my_expense_summary, list_my_recent_expenses, ...]

    Agent->>LLM: user message + available tools + system prompt
    LLM-->>Agent: tool_call → get_my_expense_summary()

    Agent->>MCP: call get_my_expense_summary  (Bearer JWT)
    MCP->>MCP: JWTVerifier → TokenClaim("sub") → user_id=42
    MCP->>DB: SELECT ... WHERE user_id=42
    DB-->>MCP: stats row
    MCP-->>Agent: {month_total: 4250, top_category: ...}

    Agent->>LLM: tool result
    LLM-->>Agent: "You've spent ₹4,250 this month..."
    Agent-->>API: final message
    API-->>User: {"response": "You've spent ₹4,250 this month..."}
```

---

## User Isolation — Security Model

The most important security property: **one user can never see or modify another user's data**, even through the AI agent.

```
JWT sub=42  →  TokenClaim("sub")="42"  →  user_id=42
                                            │
                              WHERE user_id=42  (every SQL query)
```

- The LLM **cannot pass** `user_id` to a tool — it's not an input parameter
- The MCP server **extracts** user identity from the verified JWT only
- Even if the LLM was tricked into trying `user_id=99`, the field doesn't exist in the tool schema

```python
# Tool schema exposed to the LLM (subject is hidden)
{
  "name": "list_my_recent_expenses",
  "parameters": {
    "properties": {
      "limit": {"type": "integer"}
      # user_id and subject are NOT here
    }
  }
}
```

This is verified by `test_mcp.py`:
```python
def test_tool_discovery_only_exposes_expense_tools_without_user_id(self):
    for tool in tools:
        properties = tool.parameters.get("properties", {})
        self.assertNotIn("user_id", properties)
        self.assertNotIn("subject", properties)
```

---

## Example Chatbot Conversations

**Spending summary:**
> 👤 "How much did I spend this month?"
> 🤖 "You've spent ₹4,250 in June across 12 transactions. Top category: Food & Dining at ₹1,800 (42%). Daily average: ₹303."

**Adding an expense:**
> 👤 "Add ₹450 for Swiggy, food category, UPI"
> 🤖 "Done! Added ₹450 for Swiggy under Food & Dining, paid via UPI on June 17."

**Safe delete with confirmation:**
> 👤 "Delete my Swiggy expense"
> 🤖 "I found expense #47 — Swiggy, ₹450, Food & Dining, June 17. Are you sure you want to delete it?"
> 👤 "Yes"
> 🤖 "Deleted. Expense #47 has been removed."

**Out-of-scope question blocked:**
> 👤 "What's the capital of France?"
> 🤖 "I am an expense tracking assistant and can only help with managing and analyzing your expenses."

---

## Architecture Overview

```mermaid
graph TD
    A[👤 User] --> B[FastAPI Backend]
    B --> C[JWT Auth\ncookies + Bearer]
    C --> D[/chat endpoint]
    C --> E[/api/expenses/* REST]
    C --> F[/mcp FastMCP Server]

    D --> G[build_agent access_token]
    G --> H[LangGraph ReAct Agent]
    H --> I[LLM]
    H --> J[MultiServerMCPClient\nBearer JWT]
    J --> F

    F --> K[JWTVerifier\nHS256]
    K --> L[TokenClaim sub → user_id]
    L --> M[6 MCP Tools]
    M --> N[(PostgreSQL\nSQLAlchemy)]

    E --> N

    style H fill:#7B68EE,color:#fff
    style I fill:#50C878,color:#fff
    style F fill:#FF6B6B,color:#fff
    style K fill:#F5A623,color:#fff
```

---

## Project Structure

```
app/
├── chatbot.py       ← LangGraph agent, LLM client, MCP client, memory
├── mcp_server.py    ← FastMCP server, JWTVerifier, 6 tools
├── main.py          ← FastAPI app, routes, mounts /mcp
├── security.py      ← JWT create/verify, bcrypt hash/verify
├── dependencies.py  ← get_current_user, get_db
├── database.py      ← SQLAlchemy engine, SessionLocal
├── crud/
│   ├── expense.py   ← create, search, delete, statistics
│   └── user.py      ← create, authenticate
├── models/
│   ├── expense.py   ← Expense SQLAlchemy model
│   └── user.py      ← User SQLAlchemy model
└── schemas/
    ├── expense.py   ← ExpenseCreate, ExpenseResponse, Summary
    ├── user.py      ← UserCreate, UserResponse
    ├── auth.py      ← LoginRequest
    └── chat.py      ← ChatRequest, ChatResponse
```

---

## Setup

```env
# .env
DATABASE_URL=postgresql://user:password@localhost:5432/spendly
SECRET_KEY=your-secret-key
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000
```

```bash
python -m pytest tests/ -v
```

---

## Key Design Decisions

| Decision | Reason |
|---|---|
| MCP over direct tool functions | Standard protocol — tools are discovered at runtime, not hardcoded |
| `TokenClaim("sub")` for user identity | LLM cannot inject or spoof user_id — comes from verified JWT only |
| `temperature=0` on the LLM | Financial data must be accurate, not creative |
| `InMemorySaver` with `thread_id=user_id` | Per-user conversation memory, fully isolated |
| Single ASGI app for FastAPI + MCP | One deployment, shared JWT secret, no cross-service auth complexity |
| System prompt + tool description both say "confirm before delete" | Defense in depth — two independent layers enforce safe deletion |

---

## Tests

| File | What is tested |
|---|---|
| `test_mcp.py` | Tool schema hides `user_id`, per-user data isolation, cross-user delete blocked, JWT accept/reject |
| `test_auth.py` | Bearer + cookie token, missing/invalid token → 401 |
| `test_expenses.py` | CRUD isolation, stats scoping, cross-user delete returns False |
| `test_expense_api.py` | HTTP-level: own data only, other user's expense → 404 |

---

## Future Improvements

- **PostgresSaver** — replace `InMemorySaver` so agent memory survives server restarts
- **Multi-agent** — separate agents for analysis, reporting, and budget alerts
- **Vector search** — semantic expense search ("find all food-related expenses") via pgvector
- **Streaming responses** — stream LLM tokens to the frontend for better UX
- **Budget tracking** — alert agent when a category exceeds a monthly limit
- **Refresh tokens** — extend sessions without re-login
- **Docker** — one-command local setup