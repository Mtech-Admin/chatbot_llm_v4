# File Reference - DMRC HRMS Chatbot

## Quick File Lookup

### �� Start Here
- **QUICKSTART.md** - 5-minute setup guide (start here first!)
- **README.md** - Comprehensive documentation
- **PROJECT_OVERVIEW.md** - Architecture and design
- **GETTING_STARTED.md** - Overview of what was built

### 🔧 Application Core
- **app/main.py** - FastAPI application entry point
- **app/config.py** - All settings and LLM provider switching
- **requirements.txt** - Python dependencies to install
- **.env.local** - Development configuration (Groq API)
- **.env.production** - Production configuration (vLLM)

### 🔐 Authentication & Sessions
- **app/gateway/auth.py** - JWT validation logic
- **app/gateway/session.py** - Redis session management
- **app/gateway/router.py** - HTTP endpoints (/api/chat/message, etc.)

### 🧠 Orchestration (LangGraph)
- **app/orchestrator/graph.py** - State machine for conversation flow
- **app/orchestrator/state.py** - Data structure for orchestrator state
- **app/orchestrator/intent.py** - Intent classification with LLM
- **app/orchestrator/router.py** - Routes to appropriate agent

### 🤖 Specialist Agents
- **app/agents/base.py** - Abstract base class for all agents
- **app/agents/attendance_agent.py** - Attendance specialist agent

### 🔗 External API Integration
- **app/tools/hrms_client.py** - HTTP client with JWT passthrough
- **app/tools/attendance_tools.py** - Attendance-specific tools (get_my_attendance, etc.)

### �� Data Models
- **app/models/message.py** - Pydantic models (Message, ChatRequest, etc.)

### 💾 Database & Memory
- **scripts/setup_db.py** - Database initialization script
- Database tables: chat_logs, employee_memory

### 📝 System Prompts
- **prompts/orchestrator.txt** - Instructions for the main orchestrator
- **prompts/attendance_agent.txt** - Instructions for attendance agent

### 🧪 Testing & Scripts
- **scripts/test_attendance.py** - Test suite (run to test)

### 🐳 Containerization
- **Dockerfile** - Docker image definition
- **docker-compose.yml** - Development stack (Postgres + Redis + App)

### 📚 Documentation
- **README.md** - Main documentation (500+ lines)
- **QUICKSTART.md** - Quick setup guide (200+ lines)
- **PROJECT_OVERVIEW.md** - Architecture details (400+ lines)
- **IMPLEMENTATION_SUMMARY.md** - Implementation details (300+ lines)
- **GETTING_STARTED.md** - Complete overview (200+ lines)
- **DELIVERY_CHECKLIST.md** - Project completion checklist
- **FILE_REFERENCE.md** - This file

### ⚙️ Utilities
- **.gitignore** - Git ignore patterns
- **package.json** - Project metadata

---

## File Purposes Summary

| File/Folder | Purpose | Lines |
|---|---|---|
| app/main.py | FastAPI application initialization | 70 |
| app/config.py | Settings & LLM provider setup | 60 |
| app/gateway/auth.py | JWT validation | 55 |
| app/gateway/session.py | Redis session management | 95 |
| app/gateway/router.py | HTTP endpoints | 120 |
| app/orchestrator/graph.py | LangGraph state machine | 100 |
| app/orchestrator/state.py | State data structure | 30 |
| app/orchestrator/intent.py | Intent classification | 115 |
| app/orchestrator/router.py | Agent routing | 50 |
| app/agents/base.py | Base agent class | 70 |
| app/agents/attendance_agent.py | Attendance agent | 200 |
| app/tools/hrms_client.py | HTTP client with JWT | 75 |
| app/tools/attendance_tools.py | Attendance tools | 200 |
| app/models/message.py | Data models | 80 |
| scripts/setup_db.py | Database initialization | 90 |
| scripts/test_attendance.py | Test suite | 110 |
| **Total** | **14 Python files** | **~1,636 lines** |

---

## How to Navigate

### If you want to...

**Understand the architecture**
→ Read: PROJECT_OVERVIEW.md

**Setup locally (5 min)**
→ Follow: QUICKSTART.md

**Understand what was built**
→ Read: IMPLEMENTATION_SUMMARY.md or GETTING_STARTED.md

**Configure for your HRMS API**
→ Edit: .env.local (development) or .env.production (production)

**Change LLM provider**
→ Edit: LLM_PROVIDER in .env file

**Add a new module (e.g., Leave Agent)**
→ Create: app/agents/leave_agent.py (copy from attendance_agent.py)

**Run the chatbot**
→ Command: python -m uvicorn app.main:app --reload

**Test the chatbot**
→ Command: python scripts/test_attendance.py

**Deploy with Docker**
→ Command: docker-compose up -d

**Debug an issue**
→ Read: README.md Troubleshooting section

**Understand intent classification**
→ Read: app/orchestrator/intent.py

**Understand session management**
→ Read: app/gateway/session.py

**Understand JWT handling**
→ Read: app/gateway/auth.py

**Add HRMS API integration**
→ Edit: app/tools/hrms_client.py

**Customize system prompts**
→ Edit: prompts/orchestrator.txt or prompts/attendance_agent.txt

**View API endpoints**
→ Run: python -m uvicorn app.main:app --reload
Then visit: http://localhost:8001/docs

---

## File Dependencies

```
app/main.py
  ├─ app/config.py
  ├─ app/gateway/router.py
  │   ├─ app/gateway/auth.py
  │   ├─ app/gateway/session.py
  │   └─ app/orchestrator/graph.py
  │       ├─ app/orchestrator/intent.py
  │       │   └─ app/config.py (get_llm_client)
  │       ├─ app/orchestrator/router.py
  │       │   ├─ app/agents/attendance_agent.py
  │       │   │   └─ app/tools/attendance_tools.py
  │       │   │       └─ app/tools/hrms_client.py
  │       │   └─ app/orchestrator/intent.py
  │       └─ app/gateway/session.py
  ├─ app/models/message.py
  └─ app/gateway/session.py

scripts/setup_db.py
  └─ app/config.py

scripts/test_attendance.py
  ├─ app/orchestrator/state.py
  ├─ app/orchestrator/intent.py
  └─ app/tools/attendance_tools.py
```

---

## Key Code Locations

| Component | File | Location |
|---|---|---|
| FastAPI app setup | app/main.py | Lines 1-80 |
| LLM client factory | app/config.py | Lines 50-65 |
| JWT validation | app/gateway/auth.py | Lines 8-45 |
| Session creation | app/gateway/session.py | Lines 20-40 |
| Chat endpoint | app/gateway/router.py | Lines 15-80 |
| Intent classification | app/orchestrator/intent.py | Lines 30-70 |
| LangGraph setup | app/orchestrator/graph.py | Lines 1-60 |
| Attendance agent | app/agents/attendance_agent.py | Lines 1-200 |
| HRMS API calls | app/tools/hrms_client.py | Lines 20-75 |
| Attendance tools | app/tools/attendance_tools.py | Lines 50-200 |
| Data models | app/models/message.py | Lines 1-80 |
| Database schema | scripts/setup_db.py | Lines 15-65 |
| Tests | scripts/test_attendance.py | Lines 1-110 |

---

## Configuration Files

| File | Purpose | When to Edit |
|---|---|---|
| .env.local | Development settings (Groq API) | Setup for local development |
| .env.production | Production settings (vLLM) | Setup for production |
| requirements.txt | Python dependencies | When adding new packages |
| docker-compose.yml | Docker services | When changing services |
| Dockerfile | Container image | When changing deployment |
| prompts/orchestrator.txt | Orchestrator instructions | Fine-tune chatbot behavior |
| prompts/attendance_agent.txt | Attendance agent instructions | Fine-tune attendance responses |

---

## Documentation by Purpose

| Goal | Start With | Then Read |
|---|---|---|
| Quick start | QUICKSTART.md | README.md |
| Understand code | PROJECT_OVERVIEW.md | IMPLEMENTATION_SUMMARY.md |
| Deploy | Dockerfile + docker-compose.yml | README.md (Production section) |
| Troubleshoot | README.md (Troubleshooting) | Relevant source file |
| Extend | PROJECT_OVERVIEW.md (Future Modules) | Relevant agent file |
| Test | scripts/test_attendance.py | README.md (Testing) |

---

**Last Updated**: January 2025
**Version**: 0.1.0
