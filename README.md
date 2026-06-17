# Spendly — AI-Powered Expense Tracker

Spendly is a full-stack expense tracking application that combines traditional backend development with modern AI workflows.

Users can manage expenses through both REST APIs and a natural language chatbot. The chatbot is powered by a LangGraph ReAct agent that securely interacts with expense data through a JWT-authenticated FastMCP server.

The project demonstrates backend engineering, authentication, AI agent orchestration, MCP integration, database design, and automated testing in a single application.

---

## Highlights

* JWT-secured FastAPI backend
* Expense management through REST APIs and AI chat
* FastMCP server exposing authenticated expense tools
* LangGraph ReAct agent integrated with Groq LLM
* User-scoped authorization across APIs and MCP tools
* SQLAlchemy ORM with PostgreSQL support
* Automated test suite covering authentication, CRUD operations, APIs, and MCP tools
* Single deployment architecture for FastAPI and MCP

---

## Tech Stack

| Layer          | Technology                          |
| -------------- | ----------------------------------- |
| Backend        | FastAPI                             |
| Database       | PostgreSQL, SQLAlchemy              |
| Authentication | JWT (python-jose), bcrypt (passlib) |
| MCP Server     | FastMCP                             |
| AI Agent       | LangGraph ReAct                     |
| LLM            | Groq (Llama 3.3 70B)                |
| Frontend       | Jinja2 Templates                    |
| Configuration  | pydantic-settings, .env             |
| Testing        | Pytest, unittest                    |

---

## Architecture

```text
User
 │
 ▼
Frontend
 │
 ▼
FastAPI Backend
 │
 ├── JWT Authentication
 ├── Expense REST APIs
 ├── Chat Endpoint
 └── FastMCP Server
          │
          ▼
    LangGraph Agent
          │
          ▼
       Groq LLM
          │
          ▼
      MCP Tools
          │
          ▼
     PostgreSQL
```

### Request Flow

```text
User Message
      │
      ▼
LangGraph Agent
      │
      ▼
MCP Tool Selection
      │
      ▼
FastMCP Server
      │
      ▼
Database
      │
      ▼
Response
```

---

## Key Features

### Authentication

* User registration and login
* Secure password hashing using bcrypt
* JWT-based authentication
* Support for both HttpOnly cookies and Bearer tokens
* Protected routes using FastAPI dependencies

### Expense Management

* Add expenses
* Search expenses
* Delete expenses
* View recent expenses
* Monthly spending summaries
* Category-wise spending breakdowns

### AI Chatbot

Users can interact with the application using natural language.

Examples:

```text
Add ₹450 for Swiggy under Food.
```

```text
Show my recent expenses.
```

```text
How much did I spend this month?
```

```text
Delete my last travel expense.
```

The AI agent automatically selects and executes the appropriate MCP tool before generating a response.

---

## Folder Structure

```text
expense_tracker/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── security.py
│   ├── dependencies.py
│   ├── chatbot.py
│   ├── mcp_server.py
│   ├── api/
│   ├── crud/
│   ├── models/
│   └── schemas/
│
├── templates/
│
├── tests/
│
└── requirements.txt
```

---

## Database Design

### Users

Stores application users.

| Column        | Type     |
| ------------- | -------- |
| id            | Integer  |
| username      | String   |
| email         | String   |
| password_hash | String   |
| created_at    | DateTime |

### Expenses

Stores user expenses.

| Column         | Type     |
| -------------- | -------- |
| id             | Integer  |
| user_id        | Integer  |
| amount         | Numeric  |
| category       | String   |
| description    | String   |
| payment_method | String   |
| expense_date   | Date     |
| created_at     | DateTime |

Relationship:

```text
User (1)
   │
   ▼
Expense (Many)
```

---

## Authentication & Security

Spendly uses JWT authentication for all protected operations.

Authentication flow:

```text
Signup
   │
   ▼
Password Hashing
   │
   ▼
Database Storage
   │
   ▼
Login
   │
   ▼
JWT Creation
   │
   ▼
Protected Routes
```

Security measures include:

* bcrypt password hashing
* JWT token validation
* HttpOnly authentication cookies
* User-scoped authorization
* Protected MCP tool execution
* Cross-user access prevention

Every expense operation is automatically restricted to the authenticated user.

---

## MCP Server

Spendly exposes expense functionality through a FastMCP server mounted at `/mcp`.

The MCP server acts as a secure layer between the AI agent and the application database.

### Available Tools

* get_my_expense_summary
* list_my_recent_expenses
* search_my_expenses
* get_my_category_breakdown
* add_my_expense
* delete_my_expense

All MCP tools require authentication and operate only on the authenticated user's data.

### Why MCP?

Using MCP provides:

* Standardized tool interfaces
* Dynamic tool discovery
* Better separation between AI and business logic
* Strong authorization boundaries
* Easier future integration with other AI systems

---

## AI Chatbot

The chatbot is powered by:

* LangGraph ReAct Agent
* Groq Llama 3.3 70B
* FastMCP Tools

Workflow:

```text
User Query
      │
      ▼
LangGraph Agent
      │
      ▼
Select Tool
      │
      ▼
MCP Server
      │
      ▼
Database
      │
      ▼
Final Response
```

The agent does not access the database directly. All data retrieval and modifications occur through authenticated MCP tools.

This architecture helps reduce hallucinations and ensures responses are based on real user data.

---

## API Endpoints

### Authentication

| Method | Endpoint | Description                |
| ------ | -------- | -------------------------- |
| POST   | /signup  | Register a new user        |
| POST   | /login   | Authenticate user          |
| POST   | /logout  | Logout user                |
| GET    | /me      | Current authenticated user |

### Expense API

| Method | Endpoint              | Description     |
| ------ | --------------------- | --------------- |
| GET    | /api/expenses/summary | Expense summary |
| GET    | /api/expenses/recent  | Recent expenses |
| GET    | /api/expenses/search  | Search expenses |
| POST   | /api/expenses         | Create expense  |
| DELETE | /api/expenses/{id}    | Delete expense  |

### Chat

| Method | Endpoint | Description            |
| ------ | -------- | ---------------------- |
| POST   | /chat    | Chat with AI assistant |

---

## Testing

The project includes automated tests for:

* JWT authentication
* Authorization
* Expense CRUD operations
* API endpoints
* MCP tools
* User data isolation
* Cross-user access protection

Tests run against an isolated SQLite database to ensure reliability and repeatability.

---

## Key Design Decisions

### FastAPI

Chosen for:

* High performance
* Dependency injection
* Automatic API documentation
* Strong typing support

### JWT Authentication

Chosen because it:

* Is stateless
* Scales easily
* Integrates naturally with APIs and MCP

### MCP Architecture

The AI agent never accesses the database directly.

Instead:

```text
Agent
   │
   ▼
MCP Tool
   │
   ▼
Business Logic
   │
   ▼
Database
```

This creates clear security boundaries and keeps application logic centralized.

### LangGraph

Chosen for:

* Reliable tool-calling workflows
* Memory support
* Agent orchestration
* Future multi-agent expansion

---

## Screenshots

### Landing Page

Add screenshot here.

### Login Page

Add screenshot here.

### Dashboard

Add screenshot here.

### AI Chatbot

Add screenshot here.

---

## Running Locally

### Environment Variables

Create a `.env` file:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/spendly
SECRET_KEY=your-secret-key
GROQ_API_KEY=your-groq-api-key
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Start Application

```bash
uvicorn app.main:app --reload
```

Application:

```text
http://localhost:8000
```

### Run Tests

```bash
pytest tests/
```

---

## Deployment

The FastAPI application and MCP server are deployed as a single service.

Benefits:

* Simpler deployment
* Shared authentication layer
* Shared environment configuration
* Reduced infrastructure complexity

Typical deployment platforms:

* Render
* Railway
* Fly.io
* VPS/Docker

---

## Future Improvements

* Alembic database migrations
* Redis caching
* Refresh tokens
* Budget tracking and alerts
* CSV and PDF exports
* Docker support
* Multi-currency support
* Persistent LangGraph memory
* Advanced analytics dashboard
* Multi-agent architecture

---

## Learning Outcomes

This project demonstrates practical experience with:

* FastAPI
* SQLAlchemy
* JWT Authentication
* MCP Server Development
* LangGraph Agents
* AI Tool Calling
* Secure Backend Design
* Database Modeling
* Automated Testing
* Production Deployment

---

## License

This project is intended for educational, learning, and portfolio purposes.
