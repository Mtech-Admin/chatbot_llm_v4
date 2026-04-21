# DMRC HRMS Chatbot - Project Overview

## 📁 Complete Project Structure

```
dmrc_chatbot/
├── 📄 README.md                          # Main documentation
├── 📄 QUICKSTART.md                      # 5-minute setup guide
├── 📄 IMPLEMENTATION_SUMMARY.md           # Implementation details
├── 📄 requirements.txt                    # Python dependencies
├── 📄 package.json                        # Project metadata
├── 📄 .env.local                          # Development config (Groq API)
├── 📄 .env.production                     # Production config (vLLM)
├── 📄 .gitignore                          # Git ignore rules
├── 📄 Dockerfile                          # Container image definition
├── 📄 docker-compose.yml                  # Local dev stack (Postgres + Redis + App)
│
├── 📁 app/                                # Main application package
│   ├── 📄 main.py                         # FastAPI entry point
│   ├── 📄 config.py                       # Settings & LLM provider setup
│   ├── 📄 __init__.py                     # Package marker
│   │
│   ├── 📁 gateway/                        # Layer 2: API Gateway
│   │   ├── 📄 auth.py                     # JWT validation (signature only)
│   │   ├── 📄 session.py                  # Redis session management
│   │   ├── 📄 router.py                   # FastAPI HTTP endpoints
│   │   └── 📄 __init__.py
│   │
│   ├── 📁 orchestrator/                   # Layer 3: Orchestrator (LangGraph)
│   │   ├── 📄 graph.py                    # State machine definition
│   │   ├── 📄 state.py                    # OrchestratorState schema
│   │   ├── 📄 intent.py                   # Intent classification (LLM)
│   │   ├── 📄 router.py                   # Agent routing logic
│   │   └── 📄 __init__.py
│   │
│   ├── 📁 agents/                         # Layer 4: Specialist Agents
│   │   ├── 📄 base.py                     # BaseAgent abstract class
│   │   ├── 📄 attendance_agent.py         # Attendance specialist
│   │   └── 📄 __init__.py
│   │
│   ├── 📁 tools/                          # Layer 5: Tool Definitions & Execution
│   │   ├── 📄 hrms_client.py              # HTTP client with JWT passthrough
│   │   ├── 📄 attendance_tools.py         # Attendance-specific tools
│   │   └── 📄 __init__.py
│   │
│   ├── 📁 models/                         # Data Models
│   │   ├── 📄 message.py                  # Pydantic models (Message, ChatRequest, etc.)
│   │   └── 📄 __init__.py
│   │
│   └── 📁 memory/                         # Memory Systems (placeholder)
│       └── 📄 __init__.py
│
├── 📁 prompts/                            # System Prompts
│   ├── 📄 orchestrator.txt                # Orchestrator system prompt
│   └── 📄 attendance_agent.txt            # Attendance agent system prompt
│
└── 📁 scripts/                            # Utility Scripts
    ├── 📄 setup_db.py                     # Database initialization
    └── 📄 test_attendance.py              # Test suite
```

## 🎯 How It Works

### Message Flow

```
1. CLIENT (Employee)
   └─ Sends message with JWT token
      GET /api/chat/message
      Authorization: Bearer <jwt_token>
      Body: {"message": "Show my attendance for March"}

2. GATEWAY LAYER (app/gateway/)
   └─ auth.py: Validates JWT signature
      session.py: Gets/creates session, retrieves history
      router.py: Extracts employee_id, role from JWT
   
3. ORCHESTRATOR (app/orchestrator/)
   ├─ graph.py: Executes state machine
   ├─ intent.py: Calls LLM to classify intent
   │  └─ LLM: "attendance_inquiry"
   └─ router.py: Routes to appropriate agent

4. ATTENDANCE AGENT (app/agents/attendance_agent.py)
   ├─ Gets system prompt from prompts/attendance_agent.txt
   ├─ Calls LLM with user message + tools
   ├─ LLM: "I'll get your March attendance"
   └─ LLM tool_call: get_my_attendance(month=3, year=2024)

5. TOOLS LAYER (app/tools/)
   ├─ attendance_tools.py: Execute tool
   └─ hrms_client.py: Call HRMS API
      POST /employee-attendance/my-attendance
      Authorization: Bearer <jwt_token>  ← JWT PASSTHROUGH

6. HRMS API (External)
   ├─ Validates JWT token
   ├─ Enforces authorization
   └─ Returns attendance records

7. RESPONSE
   ├─ attendance_tools.py: Format result
   ├─ LLM: Generate natural language response
   ├─ session.py: Save to Redis
   └─ router.py: Send to client
```

### Example Conversation

```
USER: "Show my attendance for March"
  ↓
ORCHESTRATOR: Classify intent → "attendance_inquiry"
  ↓
ATTENDANCE AGENT: Process with LLM + tools
  └─ Tool call: get_my_attendance(month=3, year=2024)
    └─ HRMS API returns: [
        {date: 2024-03-01, status: P, check_in: 09:30, check_out: 17:30},
        {date: 2024-03-02, status: P, check_in: 09:28, check_out: 17:45},
        ...
       ]
  └─ LLM generates response:
     "Your attendance for March 2024:
      - March 1: Present (09:30 - 17:30)
      - March 2: Present (09:28 - 17:45)
      ...
      Total Present Days: 22
      
      Would you like to see anything else about your attendance?"
  ↓
RESPONSE: "Your attendance for March 2024:..."
```

### READ-ONLY Detection

```
USER: "Apply for leave"
  ↓
ORCHESTRATOR: Detect write-action keyword "apply"
  ↓
ROUTER: Immediate redirect without LLM
  └─ Message: "I can only help you view information. 
      To apply for leave, please use the HRMS portal 
      directly at https://hrms.dmrc.internal"
  ↓
RESPONSE: Redirect message (no HRMS API call made)
```

## 🔑 Key Design Principles

### 1. Read-Only Enforcement
- Only GET endpoints called on HRMS API
- Write-intent keywords detected early
- Redirects to portal before LLM is invoked

### 2. Authorization Passthrough
- JWT token forwarded to HRMS API on every call
- HRMS API validates and enforces permissions
- Chatbot trusts API responses entirely
- Zero additional authorization logic

### 3. LLM Provider Flexibility
```
ENV: LLM_PROVIDER=groq
 └─ Groq API (llama-3.3-70b-versatile)
    - Fast, free, for development
    - API key: $0.07 per 1M input tokens

ENV: LLM_PROVIDER=vllm
 └─ vLLM (Qwen2.5-14B-Instruct-AWQ)
    - Self-hosted on AWS L4 GPU
    - One-time setup, infinite calls
    - Best for production
```
Code unchanged - only env variable switches!

### 4. Layered Architecture
```
┌─────────────────────────────────────┐
│ Client (Employee)                   │
└──────────────────┬──────────────────┘
                   │
       ┌───────────▼────────────┐
       │ Gateway Layer          │
       │ - Auth                 │
       │ - Session              │
       │ - HTTP routing         │
       └───────────┬────────────┘
                   │
       ┌───────────▼────────────┐
       │ Orchestrator (LangGraph) │
       │ - Intent classification │
       │ - Agent routing         │
       │ - State management      │
       └───────────┬────────────┘
                   │
       ┌───────────▼────────────┐
       │ Specialist Agent (LLM) │
       │ - Attendance Agent      │
       │ - Tool calling         │
       │ - Response generation  │
       └───────────┬────────────┘
                   │
       ┌───────────▼────────────┐
       │ Tools Layer            │
       │ - Tool definitions     │
       │ - HRMS HTTP client     │
       │ - JWT passthrough      │
       └───────────┬────────────┘
                   │
       ┌───────────▼────────────┐
       │ HRMS API (External)    │
       │ - Data validation      │
       │ - Authorization        │
       │ - CRUD operations      │
       └────────────────────────┘
```

Each layer has single responsibility, easy to test/modify.

### 5. Multi-Turn Memory
- Redis stores last 8 conversation turns per session
- TTL: 30 minutes
- Context injected into every LLM call
- Enables coherent multi-turn conversations

## 📊 Database Schema

### ChatLog Table
```sql
CREATE TABLE chat_logs (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(36) -- Indexed
    employee_id VARCHAR(50) -- Indexed
    message_type VARCHAR(10) -- 'user' or 'assistant'
    content TEXT,
    intent VARCHAR(50),
    routing_agent VARCHAR(50),
    tool_calls JSON,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);
```

### EmployeeMemory Table
```sql
CREATE TABLE employee_memory (
    id SERIAL PRIMARY KEY,
    employee_id VARCHAR(50) UNIQUE,
    language_preference VARCHAR(5) DEFAULT 'en',
    personality_traits JSON,
    common_queries JSON,
    created_at DATETIME,
    updated_at DATETIME
);
```

## 🚀 Deployment Stages

### Stage 1: Local Development (Current)
```
Use Groq API (free, fast)
Docker Compose: PostgreSQL + Redis + Chatbot
Run: docker-compose up -d
Test: curl -X POST http://localhost:8001/api/chat/message ...
```

### Stage 2: Testing
```
Point to HRMS staging API
Load test data into HRMS
Test with actual HRMS endpoints
Verify all attendance queries work
```

### Stage 3: Production
```
Deploy vLLM on AWS L4 GPU (g6.2xlarge)
Setup PostgreSQL managed database
Setup Redis cluster
Configure production .env
Deploy via Docker or Kubernetes
Setup monitoring/alerting
```

## 📝 Important Files to Know

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app initialization |
| `app/config.py` | All configuration, LLM provider switching |
| `app/orchestrator/graph.py` | LangGraph state machine (conversation flow) |
| `app/agents/attendance_agent.py` | Attendance specialist, tool calling logic |
| `app/tools/hrms_client.py` | HTTP client with JWT passthrough |
| `app/tools/attendance_tools.py` | Attendance tools for LLM |
| `scripts/setup_db.py` | Database initialization |
| `scripts/test_attendance.py` | Test suite |
| `.env.local` | Development settings (Groq) |
| `.env.production` | Production settings (vLLM) |

## 🔒 Security Model

### JWT Handling
```
Token received from client → Validate signature only
                           → Extract employee_id, role
                           → Forward full token to HRMS API
                           → Never decode for business logic
                           → Never cache beyond session TTL
```

### Authorization
```
"Can employee view team attendance?"
  → Only HRMS API answers this
  → Chatbot sends API call
  → API returns 403 if not authorized
  → Chatbot tells user: "You don't have access"
```

### Data Privacy
```
Session stored in Redis with 30-min TTL (auto-cleanup)
Chat logs stored in PostgreSQL (audit trail)
No sensitive data cached beyond session
No JWT tokens logged
Employee_id scoping prevents cross-employee access
```

## 🎓 Future Modules (Phase 2+)

### Leave Agent
- View leave balance
- Check leave history
- View team leave
- Holiday calendar
- Leave rules and policies

### Policy Agent (RAG-based)
- HR manual search
- Service rules
- DPE memorandums
- Leave policies
- Disciplinary procedures
- Embeds documents with BGE-M3
- Hybrid retrieval (semantic + BM25)

### Directory Agent
- Search employees by name/department
- View org chart
- See reporting hierarchy
- Team structure

## 💡 Tips for Extension

**Adding a new module (e.g., Leave Agent)**:

1. Create `app/agents/leave_agent.py`
2. Define tools in `app/tools/leave_tools.py`
3. Create system prompt in `prompts/leave_agent.txt`
4. Add intent in `app/orchestrator/intent.py` (e.g., "leave_inquiry")
5. Register in `app/orchestrator/router.py`
6. Test with `scripts/test_leave.py`

All existing infrastructure (session, auth, config, LLM) reusable!

---

**Status**: ✅ Ready for local development and testing
**Next**: Configure HRMS API connection and start testing with real data
