# DMRC HRMS Chatbot - Attendance Module

A read-only AI chatbot for the DMRC (Delhi Metro Rail Corporation) HRMS system. This chatbot helps employees view HR data through conversational AI, powered by LangGraph orchestration and LLM tool calling.

## Architecture Overview

```
┌─────────────────┐
│  Client (JWT)   │
└────────┬────────┘
         │
    ┌────▼─────────────────────┐
    │  FastAPI Gateway         │
    │  - JWT Validation        │
    │  - Session Management    │
    └────┬────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │  LangGraph Orchestrator       │
    │  ┌──────────────────────────┐ │
    │  │ 1. Intent Classification │ │
    │  │ 2. Scope Validation      │ │
    │  │ 3. Agent Routing         │ │
    │  └──────────────────────────┘ │
    └────┬──────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │  Specialist Agents (LLM)      │
    │  - Attendance Agent           │
    │  - Policy Agent (future)      │
    │  - Directory Agent (future)   │
    └────┬──────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │  Tools Layer (JWT Passthrough) │
    │  - HRMS API Client            │
    │  - Attendance Tools           │
    └────┬──────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │  HRMS REST API (Read-Only)     │
    │  - JWT Validation             │
    │  - Authorization              │
    └───────────────────────────────┘
```

## Key Features

- **Read-Only Operations Only**: Never modifies any HRMS data
- **JWT Passthrough**: Passes employee's JWT token to HRMS API for authorization
- **Intent Classification**: Uses LLM to understand employee queries
- **Specialist Agents**: Dedicated agents for different HR domains
- **LLM Provider Flexibility**: Switch between Groq (dev) and vLLM (prod) with single env variable
- **Session Management**: Redis-based conversation history and memory
- **Audit Trail**: All requests logged to PostgreSQL

## Project Structure

```
dmrc_chatbot/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   │
│   ├── gateway/
│   │   ├── auth.py             # JWT verification (signature only)
│   │   ├── session.py          # Redis session management
│   │   └── router.py           # FastAPI routes
│   │
│   ├── orchestrator/
│   │   ├── graph.py            # LangGraph state machine
│   │   ├── state.py            # Shared state schema
│   │   ├── intent.py           # Intent classification
│   │   └── router.py           # Agent routing
│   │
│   ├── agents/
│   │   ├── base.py             # Base agent class
│   │   └── attendance_agent.py # Attendance specialist agent
│   │
│   ├── tools/
│   │   ├── hrms_client.py      # HTTP client with JWT passthrough
│   │   └── attendance_tools.py # Attendance-specific tools
│   │
│   └── models/
│       └── message.py          # Pydantic data models
│
├── scripts/
│   ├── setup_db.py            # Database initialization
│   └── test_attendance.py     # Test script
│
├── .env.local                 # Development environment
├── .env.production            # Production environment
├── requirements.txt           # Python dependencies
├── package.json              # Metadata
└── README.md                 # This file
```

## Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 13+
- Redis 6+
- Groq API key (for development)

### Setup

1. **Clone and install dependencies**
```bash
cd dmrc_chatbot
pip install -r requirements.txt
```

2. **Configure environment**
```bash
# Copy dev environment
cp .env.local .env

# Edit .env with your configuration
# - Set GROQ_API_KEY (get from https://console.groq.com)
# - Set HRMS_BASE_URL (your HRMS API endpoint)
# - Set SSO_PUBLIC_KEY (for JWT verification)
```

3. **Initialize database**
```bash
python scripts/setup_db.py
```

4. **Start Redis** (if not running)
```bash
redis-server
```

5. **Run the chatbot**
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

The API will be available at `http://localhost:8001`
- Docs: http://localhost:8001/docs
- Health check: http://localhost:8001/api/chat/health

## API Endpoints

### Send Chat Message
```
POST /api/chat/message

Request:
{
  "message": "Show my attendance for March",
  "session_id": "optional-session-id",
  "language": "en"
}

Headers:
Authorization: Bearer <jwt_token>

Response:
{
  "session_id": "uuid",
  "message": "Your attendance for March 2024 shows...",
  "timestamp": "2024-01-15T10:30:00Z",
  "sources": null,
  "requires_action": false
}
```

### End Session
```
POST /api/chat/session/end?session_id=uuid

Headers:
Authorization: Bearer <jwt_token>

Response:
{
  "status": "success",
  "message": "Session ended"
}
```

### Health Check
```
GET /api/chat/health

Response:
{
  "status": "ok",
  "service": "dmrc-hrms-chatbot"
}
```

## Module: Attendance

The attendance module allows employees to view their attendance records.

### Available Operations

1. **View Personal Attendance**
   - Get attendance records for a specific month/year
   - View daily attendance for a specific date
   - See attendance status (Present, Absent, Leave, etc.)

2. **Manager Features**
   - View team's daily attendance
   - Bulk view for date ranges

### Example Queries

- "Show my attendance for March"
- "What's my attendance today?"
- "When did I check in yesterday?"
- "Show team attendance for this week" (managers only)

### Attendance Tools

```python
# Available to LLM
get_my_attendance(month, year, page=1, limit=20)
get_my_daily_attendance(date)
get_team_attendance(date, from_date, to_date)  # Managers only
```

### API Reference

**My Attendance** → HRMS `/employee-attendance/my-attendance` (POST)
```json
{
  "month": "3",
  "year": "2024",
  "page": 1,
  "limit": 20
}
```

**My Daily Attendance** → HRMS `/employee-attendance/my-daily-attendance` (POST)
```json
{
  "date": "2024-03-15"
}
```

**Team Daily Attendance** → HRMS `/employee-attendance/team-daily-attendance` (POST)
```json
{
  "date": "2024-03-15"
}
or
{
  "from_date": "2024-03-01",
  "to_date": "2024-03-31"
}
```

## LLM Configuration

### Development (Groq API)

Fast, free inference via Groq API. Perfect for testing.

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
```

Model: **llama-3.3-70b-versatile** (best for tool calling)

Get API key: https://console.groq.com

### Production (vLLM)

Self-hosted on AWS g6.2xlarge (NVIDIA L4 24GB) for cost efficiency.

```bash
LLM_PROVIDER=vllm
VLLM_BASE_URL=http://localhost:8000/v1
```

Model: **Qwen2.5-14B-Instruct-AWQ** (Q4 quantized)

Launch vLLM:
```bash
python -m vllm.entrypoints.openai.api_server \
  --model Qwen/Qwen2.5-14B-Instruct-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.85 \
  --max-model-len 16384 \
  --max-num-seqs 8 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --port 8000
```

## Authorization Model

**CRITICAL**: The chatbot performs ZERO authorization checks. All authorization is delegated to the HRMS API.

```
Employee sends JWT → Chatbot forwards to HRMS API → API enforces permissions
```

Examples:
- If user asks for team attendance but is not a manager, HRMS API returns 403
- If user asks for peer's attendance, HRMS API returns 403
- Chatbot never decodes JWT for business logic - only validates signature

## Read-Only Enforcement

The chatbot detects write-intent requests and redirects:

```
User: "Apply for leave"
↓
Intent Classifier: "redirect_to_portal"
↓
Response: "I can help you view information, but I'm not able to apply for leave. 
Please use the HRMS portal directly: https://hrms.dmrc.internal"
```

**Detected Write Actions**:
- apply, submit, update, change, create, add, upload
- approve, reject, cancel, delete, remove, modify
- register, enroll, subscribe
- check-in, checkout

## Session & Memory

### Short-term (Redis)

- Last 8 conversation turns per session
- TTL: 30 minutes
- Injected into system prompt for context

### Long-term (PostgreSQL)

- Employee preferences (language, response style)
- Frequently asked topics
- Personality traits extracted from sessions
- Used to personalize responses

## Testing

Run the test suite:

```bash
python scripts/test_attendance.py
```

Tests cover:
- Intent classification
- Read-only constraint validation
- Tool definitions

## Policy Q&A Knowledge Base (Excel Upload)

For policy/leave FAQ questions, the chatbot can retrieve from an Excel/CSV file with these columns:

- `question`
- `answer`

### Upload/ingest steps

1. Put your file anywhere on disk (for example: `data/policy_qa.xlsx`)
2. Run ingestion:

```bash
PYTHONPATH=. ./.venv/bin/python scripts/ingest_policy_qa.py --file "/absolute/path/to/policy_qa.xlsx" --replace
```

3. Ask policy questions in chat, for example:
   - "What leaves are admissible to those engaged on PRCE basis?"

Notes:
- Use `--replace` to clear old rows before loading new sheet.
- Supports `.xlsx` and `.csv`.
- For `.xlsx`, install `openpyxl` if missing: `./.venv/bin/pip install openpyxl`

## Development Roadmap

### Phase 1 (Current)
- ✅ Attendance module
- ✅ Intent classification
- ✅ LangGraph orchestration
- ✅ JWT passthrough

### Phase 2
- Leave & vacation management
- Policy RAG (HR policies, circulars, rules)
- Employee directory search

### Phase 3
- Payslip viewing
- IT helpdesk integration
- Reimbursement tracking

## Troubleshooting

### "No attendance records found"
- Check HRMS API is running
- Verify JWT token is valid
- Ensure date range has records in HRMS

### "Access denied"
- User doesn't have permission for that operation
- Check user role in HRMS
- Verify JWT claims

### "LLM timeout"
- Groq API is rate-limited: wait 30s and retry
- vLLM server is down: check `curl http://localhost:8000/health`
- Internet connection issue

### Redis connection error
- Start Redis: `redis-server`
- Check REDIS_URL in .env
- Default: `redis://localhost:6379`

## Contributing

This chatbot follows DMRC HRMS architecture patterns. When adding new features:

1. Create new agent in `app/agents/`
2. Add tools in `app/tools/`
3. Define system prompt in `prompts/`
4. Register in orchestrator router
5. Test with `scripts/test_*.py`

## Security Notes

- JWT tokens are never stored or decoded for business logic
- All tokens passed through to HRMS API for verification
- Session IDs are UUIDs, not predictable
- Redis sessions have 30-minute TTL
- Chat logs stored separately from sessions
- No sensitive data cached beyond session TTL

## Performance

- Groq API: ~1-2s response time
- vLLM (L4): ~500ms-1s response time
- Session retrieval: <10ms (Redis)
- HRMS API calls: ~2-3s (depends on HRMS load)

## License

UNLICENSED - DMRC Internal Use Only

## Support

For issues, contact the DMRC IT team.
