# Quick Start Guide - DMRC HRMS Chatbot

## 5-Minute Setup

### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Set environment variables
export GROQ_API_KEY="your_groq_api_key"
export SSO_PUBLIC_KEY="your_sso_public_key"

# 2. Start all services
docker-compose up -d

# 3. Initialize database
docker-compose exec chatbot python scripts/setup_db.py

# 4. Test the chatbot
curl -X POST http://localhost:8001/api/chat/health
```

### Option 2: Local Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start PostgreSQL and Redis
# On macOS with Homebrew:
brew services start postgresql
brew services start redis

# Or use Docker:
docker-compose up -d postgres redis

# 3. Configure environment
cp .env.local .env
# Edit .env with your credentials

# 4. Initialize database
python scripts/setup_db.py

# 5. Run the chatbot
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## Testing the Chatbot

### 1. Get a JWT Token

You need a valid JWT token from your DMRC SSO. For testing, you can create a mock token:

```bash
# Generate a test JWT (requires pyjwt)
python -c "
import jwt
import json
payload = {
    'employee_id': 'test_emp_001',
    'empId': 'test_emp_001',
    'role': 'employee',
    'email': 'test@dmrc.in'
}
token = jwt.encode(payload, 'secret_key', algorithm='HS256')
print(token)
"
```

### 2. Send a Chat Message

```bash
curl -X POST http://localhost:8001/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
  -d '{
    "message": "Show my attendance for March",
    "language": "en"
  }'
```

### 3. Test Attendance Data

Create a session and send multiple messages:

```bash
# First message (creates session)
curl -X POST http://localhost:8001/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"message": "What is my attendance for March 2024?"}' \
  | jq '.session_id' > session.txt

SESSION_ID=$(cat session.txt | tr -d '"')

# Follow-up message (uses same session)
curl -X POST http://localhost:8001/api/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d "{\"message\": \"Show today's attendance\", \"session_id\": \"$SESSION_ID\"}"
```

## Running Tests

```bash
# Test intent classification and read-only validation
python scripts/test_attendance.py

# Run with pytest
pytest tests/ -v
```

## Verifying Setup

### Check Health
```bash
curl http://localhost:8001/api/chat/health
# Response: {"status": "ok", "service": "dmrc-hrms-chatbot"}
```

### Check Documentation
Open browser: http://localhost:8001/docs
(Swagger UI for testing endpoints)

### Check Redis Connection
```bash
redis-cli ping
# Response: PONG
```

### Check PostgreSQL Connection
```bash
psql postgresql://chatbot:chatbot_dev@localhost:5432/hrms_chatbot -c "SELECT * FROM information_schema.tables WHERE table_schema = 'public';"
```

## Common Issues

### "GROQ_API_KEY not set"
```bash
export GROQ_API_KEY="gsk_your_key_here"
```
Get key from: https://console.groq.com/api-keys

### "Redis connection refused"
```bash
# Start Redis
redis-server

# Or with Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### "PostgreSQL connection refused"
```bash
# Start PostgreSQL
brew services start postgresql

# Or with Docker
docker-compose up -d postgres
```

### "HRMS API not reachable"
- Ensure your HRMS API is running
- Check HRMS_BASE_URL in .env points to correct endpoint
- Verify JWT token is valid for the HRMS API

### "JWT validation failed"
- Check SSO_PUBLIC_KEY in .env matches your SSO system
- Ensure token hasn't expired
- Verify token is in "Bearer <token>" format

## Next Steps

1. **Configure HRMS Integration**
   - Set HRMS_BASE_URL to your actual HRMS API
   - Configure SSO_PUBLIC_KEY for JWT validation
   - Test attendance API connectivity

2. **Load Test Data**
   - Create test employees in HRMS
   - Generate attendance records for testing
   - Verify API responses with different user roles

3. **Customize System Prompts**
   - Edit prompts/orchestrator.txt
   - Edit prompts/attendance_agent.txt
   - Fine-tune for your organization's tone

4. **Add More Modules**
   - Leave module (see Phase 2 in README)
   - Policy RAG (HR documents)
   - Employee directory

## Support

For issues:
1. Check logs: `docker-compose logs chatbot`
2. Review README.md for detailed documentation
3. Check .env configuration
4. Verify all services are running

## Production Deployment

See README.md section "Production Deployment" for:
- vLLM setup on AWS L4 GPU
- Production environment configuration
- Security considerations
- Performance optimization
