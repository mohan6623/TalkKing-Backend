# TalkKing API

AI-powered communication coaching platform that analyzes speech recordings across six dimensions and delivers actionable feedback to help users become confident speakers.

Built with **FastAPI**, powered by **Groq Whisper**, **Hume AI**, and **Google Gemini** running in a parallel analysis pipeline.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | FastAPI | REST API server |
| Server | Uvicorn | ASGI application server |
| Language | Python 3.11+ | Backend runtime |
| Auth | Supabase Auth | JWT-based auth (email/password + OAuth) |
| Database | PostgreSQL (Supabase) | User data, sessions, feedback reports |
| Cache / Broker | Redis 7 | Rate limiting, Celery task broker |
| Task Queue | Celery | Asynchronous audio analysis |
| Transcription | Groq Whisper v3 | Speech-to-text + filler word detection |
| Vocal Analysis | Hume AI Prosody | Emotion & acoustic analysis |
| Language AI | Google Gemini 1.5 Flash | Boldness & confidence scoring |
| Email | Mailgun | Post-analysis notifications |
| Monitoring | Sentry | Error tracking |
| Validation | Pydantic v2 | Request/response schemas |
| Containerization | Docker | Production deployment |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Redis server
- Supabase project (for auth + PostgreSQL)
- API keys for Groq, Hume AI, and Google Gemini

### Installation

```bash
# Clone and enter backend directory
cd Backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# For development (includes testing, linting, type checking)
pip install -r requirements-dev.txt
```

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | `production` / `staging` / `development` |
| `SUPABASE_URL` | Yes | — | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | — | Supabase admin key (bypasses RLS) |
| `SUPABASE_JWT_SECRET` | Yes | — | JWT signing secret |
| `SUPABASE_ANON_KEY` | Yes | — | Supabase anonymous key |
| `GROQ_API_KEY` | Yes | — | Groq API key for transcription |
| `GEMINI_API_KEY` | Yes | — | Google Gemini API key |
| `HUME_API_KEY` | Yes | — | Hume AI API key |
| `REDIS_URL` | No | `redis://127.0.0.1:6379/0` | Redis connection URL |
| `CELERY_BROKER_URL` | No | `redis://127.0.0.1:6379/1` | Celery broker URL |
| `CORS_ORIGINS` | No | See config | Allowed frontend origins |
| `MAILGUN_API_KEY` | Yes | — | Mailgun API key |
| `MAILGUN_DOMAIN` | No | `mail.talkking.me` | Mailgun sending domain |
| `SENTRY_DSN` | No | — | Sentry error tracking DSN |

### Run

```bash
# Start the API server (development with hot-reload)
make dev

# Start the Celery worker (separate terminal)
make worker

# Or run directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## Docker

```bash
# Development (API + Redis + Celery worker)
docker compose up

# With Celery Flower monitoring dashboard
docker compose --profile monitoring up

# Production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
docker compose logs -f --tail=100
```

**Services:**

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI server |
| `redis` | 6379 | Cache + task broker |
| `celery-worker` | — | Background audio analysis |
| `flower` | 5555 | Celery monitoring (optional) |

---

## API Endpoints

### Authentication (Public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/signup` | Register new user |
| `POST` | `/api/v1/auth/login` | Login with email/password |
| `GET` | `/api/v1/auth/oauth/{provider}` | Initiate OAuth flow (google/github) |
| `POST` | `/api/v1/auth/oauth/callback` | Exchange PKCE code for token |

### Users (Protected)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/users/me` | Get current user profile |
| `PATCH` | `/api/v1/users/me` | Update profile fields |

### Sessions (Protected)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/sessions` | Create a recording session |
| `POST` | `/api/v1/sessions/{id}/analyze` | Upload audio for analysis |
| `GET` | `/api/v1/sessions/{id}/status` | Poll analysis status |

### Feedback (Protected)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/sessions/{id}/feedback` | Get AI feedback report |

### Progress & History (Protected)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/progress` | Historical scores for charts |
| `GET` | `/api/v1/history` | Paginated session history |

### Demo Assessment (Public — Rate Limited)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/demo/assess` | Anonymous demo assessment (5 req/hr per IP) |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health (Redis + Supabase checks) |

---

## AI Analysis Pipeline

Audio recordings are analyzed through a 3-phase pipeline using Celery for async processing:

```
┌─────────────────────────────────────────────────────┐
│  Phase 1 — Parallel                                 │
│  ┌──────────────────┐  ┌─────────────────────────┐  │
│  │  Groq Whisper v3  │  │  Hume AI Prosody        │  │
│  │  ─ Transcription  │  │  ─ Pitch variation      │  │
│  │  ─ Filler words   │  │  ─ Breathing patterns   │  │
│  │  ─ WPM count      │  │  ─ Vocal fry/raspiness  │  │
│  └────────┬─────────┘  └─────────────┬───────────┘  │
│           │                          │               │
├───────────▼──────────────────────────▼───────────────┤
│  Phase 2 — Sequential                               │
│  ┌──────────────────────────────────────────┐        │
│  │  Google Gemini 1.5 Flash                 │        │
│  │  ─ Confidence/boldness scoring           │        │
│  │  ─ Weak phrase detection                 │        │
│  │  ─ Hedging language analysis             │        │
│  └────────────────────┬─────────────────────┘        │
│                       │                              │
├───────────────────────▼──────────────────────────────┤
│  Phase 3 — Scoring                                   │
│  ┌──────────────────────────────────────────┐        │
│  │  Feedback Engine                         │        │
│  │  ─ 6-dimension scores (0–100)            │        │
│  │  ─ Improvements + strengths              │        │
│  │  ─ Personalized tips                     │        │
│  │  ─ Confidence layer recommendation (1–6) │        │
│  └──────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────┘
```

**Six Scoring Dimensions:**

| Dimension | Source | Description |
|-----------|--------|-------------|
| Clarity | Groq | Speech clarity, filler word rate, WPM |
| Vocal Quality | Hume | Breathing, vocal fry, raspiness |
| Musicality | Hume | Pitch variation, monotone detection |
| Boldness | Gemini | Confidence language, weak phrase avoidance |
| Eye Contact | Video only | Gaze tracking (when video provided) |
| Body Language | Video only | Posture and gesture analysis |

---

## Database Schema

Uses PostgreSQL via Supabase with Row-Level Security:

| Table | Purpose |
|-------|---------|
| `profiles` | User accounts, mission/weakness, progress metrics (level, streak, best score, avg WPM) |
| `sessions` | Recording metadata — type, prompt, duration, status lifecycle |
| `feedback_reports` | AI analysis results — per-dimension scores, improvements, tips, confidence layer |

---

## Project Structure

```
Backend/
├── app/
│   ├── main.py                 # FastAPI app factory + lifespan
│   ├── config.py               # Pydantic settings (env vars)
│   ├── dependencies.py         # Shared FastAPI dependencies
│   ├── api/
│   │   ├── router.py           # Route aggregator
│   │   └── v1/                 # Versioned endpoints
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── sessions.py
│   │       ├── feedback.py
│   │       ├── progress.py
│   │       ├── history.py
│   │       └── assessment.py
│   ├── core/
│   │   ├── security.py         # JWT validation, auth dependency
│   │   ├── supabase_client.py  # Supabase admin/anon clients
│   │   ├── redis_client.py     # Redis connection pool
│   │   └── exceptions.py       # Custom exception classes
│   ├── schemas/                # Pydantic v2 request/response models
│   ├── services/
│   │   ├── ai_orchestrator.py  # 3-phase parallel AI pipeline
│   │   ├── groq_service.py     # Speech transcription
│   │   ├── hume_service.py     # Acoustic analysis
│   │   ├── gemini_service.py   # Boldness analysis
│   │   ├── feedback_engine.py  # Score calculation
│   │   ├── email_service.py    # Mailgun notifications
│   │   ├── user_service.py     # Profile CRUD
│   │   └── audio_utils.py      # File validation
│   └── tasks/
│       ├── celery_app.py       # Celery initialization
│       └── analysis.py         # Async analysis task
├── tests/                      # pytest test suite
├── infra/                      # Deployment configs (nginx, supervisor, redis)
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
├── requirements.txt
└── requirements-dev.txt
```

---

## Development Commands

```bash
make dev            # Run dev server with hot-reload
make worker         # Start Celery worker
make flower         # Celery monitoring dashboard (port 5555)
make test           # Run all tests
make test-cov       # Tests with coverage report (70% threshold)
make lint           # Check code with ruff
make fmt            # Format code with ruff
make type-check     # Run mypy type checking
make install        # Install production dependencies
make install-dev    # Install dev + test dependencies
make docker-build   # Build Docker images
make docker-up      # Start Docker Compose
make docker-down    # Stop Docker Compose
make docker-logs    # Stream Docker logs
```

---

## Testing

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
python -m pytest tests/test_routes.py -v

# Run specific test
python -m pytest tests/test_routes.py::test_health_check -v
```

---

## Deployment

Production deployment uses Docker Compose with Nginx reverse proxy and Supervisor process management:

```bash
# Build and deploy
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Or use the deploy script
bash infra/deploy.sh
```

Resource limits in production:
- **API:** 2 CPUs, 1 GB RAM
- **Celery Worker:** 2 CPUs, 2 GB RAM

---

## License

Proprietary — All rights reserved.
