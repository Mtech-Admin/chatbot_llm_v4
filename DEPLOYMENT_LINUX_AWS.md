# DMRC Chatbot — deployment plan (Linux on AWS)

This document is a practical, ordered checklist for running `dmrc_chatbot` on AWS. Adjust names (VPC, subnets, security groups) to match your org’s standards.

## Architecture (recommended)

| Component | AWS option | Notes |
|-----------|------------|--------|
| API (FastAPI + Uvicorn) | **Amazon EC2** (Docker or systemd) or **ECS Fargate** | Dockerfile already targets port **8001**. |
| PostgreSQL | **Amazon RDS for PostgreSQL** | App builds `DATABASE_URL` from `POSTGRES_*` in `app/config.py`. |
| Redis (sessions) | **Amazon ElastiCache for Redis** | `REDIS_URL` in settings. |
| HRMS backend | Your existing service | Set `HRMS_BASE_URL` to the reachable URL (private ALB/NLB or VPN). |
| LLM | **Groq** (default) or **vLLM** on EC2/GPU | `LLM_PROVIDER`, `GROQ_API_KEY` or `VLLM_BASE_URL`. |
| TLS | **Application Load Balancer + ACM** or **Nginx + Let’s Encrypt** | Terminate HTTPS in front of the app. |
| Secrets | **AWS Secrets Manager** or **SSM Parameter Store** | Prefer not to store keys only in plain `.env` on disk. |

---

## Phase 1 — AWS networking and access

1. **VPC**  
   Use an existing VPC or create one with public subnets (for ALB/bastion) and **private subnets** for app + RDS + Redis if possible.

2. **Security groups**  
   - **ALB**: inbound `443` (and `80` if redirecting to HTTPS) from the internet or your corporate IP range.  
   - **App (EC2/ECS)**: inbound **only** from the ALB security group on port **8001** (or the port you map).  
   - **RDS**: inbound **5432** only from the app security group.  
   - **Redis**: inbound **6379** only from the app security group.  
   - **Outbound**: allow HTTPS to Groq (`api.groq.com`) and to `HRMS_BASE_URL`; tighten with VPC endpoints if you use private subnets without NAT.

3. **SSH or SSM**  
   Prefer **AWS Systems Manager Session Manager** so EC2 does not need open SSH from `0.0.0.0/0`. If you use SSH, restrict the source IP.

---

## Phase 2 — Data stores

1. **RDS PostgreSQL (shared with DMRC_HRMS_API)**  
   - Use the **same** database (and credentials) as the Nest HRMS API, or set `CHATBOT_DATABASE_URL` to that full connection string.  
   - Run HRMS TypeORM migrations so `policy_qa` and `chatbot_conversations` exist before starting the chatbot.  
   - Enable backups and Multi-AZ if required by policy.

2. **Elastiache Redis**  
   - Create a cluster in the same VPC; use the primary endpoint in `REDIS_URL` (e.g. `rediss://...` if TLS is enabled — confirm client support in your `redis` usage).

3. **Optional: run Postgres/Redis on the same EC2**  
   Possible for non-production only; not recommended for production (scaling, backups, patching).

---

## Phase 3 — Application configuration

1. **Environment variables** (align with `app/config.py`):  
   - **LLM**: `LLM_PROVIDER`, `GROQ_API_KEY` (or `VLLM_BASE_URL` for vLLM).  
   - **HRMS**: `HRMS_BASE_URL`, `HRMS_TIMEOUT`.  
   - **Auth**: `SSO_PUBLIC_KEY`, `SECRET_KEY` (use a long random value in production).  
   - **Database**: `POSTGRES_HOST`, `POSTGRES_LOCAL_PORT`, `POSTGRES_USERNAME`, `POSTGRES_PASSWORD`, `POSTGRES_DATABASE` (or supply a full URL if you extend settings).  
   - **Redis**: `REDIS_URL`, `SESSION_TTL`, `MEMORY_TTL`.  
   - **App**: `DEBUG=false`.

2. **Secrets**  
   Load secrets at runtime from Secrets Manager/SSM and export env vars in **systemd** `EnvironmentFile` or Docker `env_file` generated at boot — avoid committing `.env.local`.

3. **CORS**  
   Update `allow_origins` in `app/main.py` to your real frontend origin(s) before go-live.

---

## Phase 4 — Deploy the API on Linux (EC2)

### Option A — Docker (matches existing `Dockerfile`)

1. Install Docker on Amazon Linux 2022 / Ubuntu LTS.  
2. Copy the repo (or pull from CI) to the server; build:  
   `docker build -t dmrc-chatbot .`  
3. Run with env from a secure file or orchestration:  
   `docker run -d --restart unless-stopped -p 127.0.0.1:8001:8001 --env-file /path/to/prod.env dmrc-chatbot`  
4. Bind to **127.0.0.1** if Nginx/ALB terminates TLS on the same host; otherwise place the container behind an ALB in private subnets.

### Option B — systemd + Python venv

1. Install Python 3.11+ (match `Dockerfile`).  
2. Create a dedicated user (e.g. `chatbot`).  
3. `python -m venv /opt/dmrc-chatbot/venv && source venv/bin/activate && pip install -r requirements.txt`  
4. Systemd unit: `ExecStart=/opt/dmrc-chatbot/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8001`  
   WorkingDirectory=/opt/dmrc-chatbot (repo root).  
5. `systemctl enable --now dmrc-chatbot`.

---

## Phase 5 — Reverse proxy and TLS

1. **ALB (recommended on AWS)**  
   - Target group: HTTP to EC2/ECS on port 8001 (or Nginx port).  
   - Listener **443** with ACM certificate.  
   - Health check: HTTP `GET /api/chat/health` (or `/` as per your ops preference).

2. **Nginx on EC2**  
   - Proxy `proxy_pass http://127.0.0.1:8001;`  
   - Set `X-Forwarded-*` headers for correct client IP if needed.

---

## Phase 6 — First deploy and schema

1. Start the app; confirm **`GET /`** and **`GET /api/chat/health`** respond.  
2. Run **DMRC_HRMS_API** TypeORM migrations on the shared Postgres database (`policy_qa`, `chatbot_conversations`). The chatbot does not apply DDL at startup.  
3. Run any **knowledge ingest** jobs your team uses (`app/knowledge/ingest.py`) if policy Q&A data must be loaded in production.

---

## Phase 7 — Operations

1. **Logs**: ship stdout/stderr to **CloudWatch Logs** (Docker `awslogs` driver or `journald` + CloudWatch agent).  
2. **Metrics & alarms**: ALB 5xx, target health, RDS CPU/storage, Redis memory.  
3. **Backups**: RDS automated backups; document restore drill.  
4. **Updates**: pin image tags or git SHA in deploy; roll out via new task definition / new AMI / blue-green as you mature.

---

## Quick verification checklist

- [ ] RDS and Redis reachable only from the app.  
- [ ] `HRMS_BASE_URL` reachable from the app (routing/DNS/firewall).  
- [ ] Groq (or vLLM) reachable; API key valid.  
- [ ] JWT/SSO public key and `SECRET_KEY` set for production.  
- [ ] CORS matches production frontend.  
- [ ] HTTPS end-to-end for browser clients.  
- [ ] Health checks green on the load balancer.

This sequence gets a minimal production path; for higher availability, add multi-AZ RDS, redundant app instances behind an ALB, and automated CI/CD (CodePipeline, GitHub Actions → ECR → ECS, etc.).
