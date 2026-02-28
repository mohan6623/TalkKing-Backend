# TalkKing Backend — Quality Assurance & Improvement Report

> **Audit Date:** March 9, 2026
> **Codebase:** TalkKing Backend (FastAPI / Python 3.11+)
> **Auditor:** Automated deep-code analysis
> **Scope:** Security, reliability, code quality, testing, deployment, best practices

---

## Quick Stats

| Severity     | Count | Status       |
|--------------|-------|--------------|
| **CRITICAL** | 1     | Must fix NOW |
| **HIGH**     | 6     | Fix this week |
| **MEDIUM**   | 25    | Fix this sprint |
| **LOW**      | 20+   | Fix when convenient |

---

## Table of Contents

1. [Architecture Strengths](#1-architecture-strengths)
2. [CRITICAL Issues](#2-critical-issues)
3. [HIGH Severity Issues](#3-high-severity-issues)
4. [MEDIUM Severity Issues](#4-medium-severity-issues)
5. [LOW Severity Issues](#5-low-severity-issues)
6. [Testing Gaps](#6-testing-gaps)
7. [Missing Best Practices](#7-missing-best-practices)
8. [Phased Action Plan](#8-phased-action-plan)

---

## 1. Architecture Strengths

Before diving into issues, here is what the codebase already does well:

| Area | What's Done Right |
|------|-------------------|
| **App Lifecycle** | Uses modern FastAPI `lifespan` context manager (`app/main.py:21-32`) instead of deprecated `on_startup`/`on_shutdown` |
| **Separation of Concerns** | Clean layered architecture: Routes (thin controllers) -> Schemas (Pydantic v2) -> Services (business logic) -> Core (infrastructure) -> Tasks (async workers) |
| **Pydantic v2** | Correct use of `ConfigDict`, `model_dump(exclude_unset=True)`, `alias_generator=to_camel`, `populate_by_name=True` across all schemas |
| **Async Safety** | All synchronous Supabase calls wrapped with `await asyncio.to_thread(lambda: ...)` to prevent blocking the event loop |
| **Graceful Degradation** | AI services (Hume, Gemini, Groq) return neutral defaults on failure instead of crashing the pipeline |
| **Data Ownership** | Every DB query filters by `user_id` from the JWT, preventing cross-user data access |
| **Atomic Signup** | Profile creation rolls back the auth user if the profile insert fails (`app/api/v1/auth.py:77-97`) |
| **Celery Config** | Production-ready: `task_acks_late=True`, `worker_prefetch_multiplier=1`, `worker_max_tasks_per_child=100` |
| **Docker** | Multi-stage build with non-root user (`talkking`), health checks, `PYTHONUNBUFFERED=1` |
| **Nginx** | TLS 1.2+, strong ciphers, rate limiting (auth: 5r/m, API: 30r/m), security headers, `server_tokens off` |
| **AI Orchestrator** | Textbook parallel fan-out: Phase 1 (Groq + Hume parallel) -> Phase 2 (Gemini sequential) -> Phase 3 (score calculation) |
| **Mass Assignment Protection** | `user_service.py:38` uses an allowlist of updatable fields (`name`, `avatar`, `mission`, `weakness`) |

---

## 2. CRITICAL Issues

### 2.1 — Production Secrets Exposed in `.env` File

| | |
|---|---|
| **File** | `.env` (root directory) |
| **Impact** | Full database admin access, API key abuse, financial liability |
| **Risk** | An attacker with access to this file can bypass Row Level Security, read/write all user data, and run up AI API bills |

**Problem:** The `.env` file contains real production secrets on disk:
- `SUPABASE_SERVICE_KEY` — bypasses RLS, grants full admin DB access
- `SUPABASE_JWT_SECRET` — allows forging valid JWTs for any user
- `GROQ_API_KEY`, `GEMINI_API_KEY`, `HUME_API_KEY` — billable AI API keys
- `SENTRY_DSN`, `DATADOG_API_KEY` — monitoring credentials

**Solution (Immediate):**

1. **Rotate ALL secrets** in their respective dashboards (Supabase, Groq, Gemini, Hume, Sentry, Datadog)
2. **Verify git history** for past commits containing secrets:
   ```bash
   # Check if .env was ever committed
   git log --all --full-history -- .env

   # If found, use BFG or git-filter-repo to purge history
   # Then force-push (coordinate with team)
   ```
3. **Ensure `.env` is in `.gitignore`** (it already is at line 4, but verify):
   ```gitignore
   .env
   .env.*
   !.env.example
   ```
4. **Use a secrets manager** in production (e.g., Docker Secrets, AWS Secrets Manager, or Doppler)

---

## 3. HIGH Severity Issues

### 3.1 — No Password Validation on Signup

| | |
|---|---|
| **File** | `app/api/v1/auth.py:27` |
| **Impact** | Users can register with empty or single-character passwords |
| **Category** | Security |

**Problem:** The `SignupRequest` model accepts any string for `password`, including `""` (empty) or `"a"`:
```python
# CURRENT (auth.py:25-29)
class SignupRequest(BaseModel):
    email: EmailStr
    password: str          # <-- No validation at all
    name: str
```

**Solution:**
```python
# FIXED
from pydantic import BaseModel, EmailStr, field_validator
import re

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    redirect_to: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(v) > 128:
            raise ValueError("Password must not exceed 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1 or len(v) > 100:
            raise ValueError("Name must be between 1 and 100 characters")
        return v
```

---

### 3.2 — Entire Audio File Read Into Memory Before Size Validation

| | |
|---|---|
| **File** | `app/api/v1/sessions.py:72` and `app/api/v1/assessment.py:65` |
| **Impact** | A 25MB upload consumes 25MB of server RAM before any validation occurs. Attackers can exhaust memory with concurrent large uploads |
| **Category** | Reliability / Security |

**Problem:**
```python
# CURRENT (sessions.py:72-76)
audio_bytes = await audio.read()       # <-- entire file in memory FIRST
if not validate_audio_size(audio_bytes):  # <-- THEN check size
    raise AudioTooLargeError()
```

**Solution — Check Content-Length header first, then stream with a cap:**
```python
# FIXED
MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB

@router.post("/{session_id}/analyze", response_model=AnalyzeResponse)
async def analyze_session(
    session_id: str,
    request: Request,
    audio: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    # Pre-check Content-Length header (cheap, no I/O)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_AUDIO_BYTES:
        raise AudioTooLargeError()

    # Stream with a hard cap to prevent memory exhaustion
    chunks = []
    total_size = 0
    while chunk := await audio.read(8192):  # 8KB chunks
        total_size += len(chunk)
        if total_size > MAX_AUDIO_BYTES:
            raise AudioTooLargeError()
        chunks.append(chunk)

    audio_bytes = b"".join(chunks)
    # ... rest of handler
```

Apply the same fix to `assessment.py:65` with `MAX_AUDIO_BYTES = 10 * 1024 * 1024` (10MB for demo).

---

### 3.3 — Synchronous AI Pipeline in Demo HTTP Handler (60+ Second Blocking)

| | |
|---|---|
| **File** | `app/api/v1/assessment.py:73` |
| **Impact** | Each demo request blocks a Uvicorn worker for 60+ seconds. Under load, this exhausts the worker pool and makes the entire API unresponsive |
| **Category** | Reliability |

**Problem:**
```python
# CURRENT (assessment.py:70-73)
# Run analysis directly (synchronous for demo — short audio only)
from app.services.ai_orchestrator import analyze_recording
session_id = str(uuid.uuid4())
feedback = await analyze_recording(audio_bytes, "tech-interview", session_id)
# ^^ This blocks the worker for 60+ seconds while Hume polls
```

**Solution — Add a timeout wrapper:**
```python
# FIXED — Wrap with asyncio.wait_for to cap execution time
import asyncio

try:
    feedback = await asyncio.wait_for(
        analyze_recording(audio_bytes, "tech-interview", session_id),
        timeout=45.0,  # Hard cap at 45 seconds
    )
except asyncio.TimeoutError:
    raise HTTPException(
        status_code=504,
        detail="Analysis took too long. Please try with a shorter recording.",
    )
```

**Better long-term solution:** Move demo analysis to Celery like authenticated sessions, and have the frontend poll for results via a status endpoint.

---

### 3.4 — Redis Running Without Authentication

| | |
|---|---|
| **File** | `infra/redis/redis.conf:6-8` |
| **Impact** | Any machine on the network can connect to Redis, read/write data, and execute commands. This is a well-known attack vector (Redis crypto-mining exploits) |
| **Category** | Security |

**Problem:**
```conf
# CURRENT (redis.conf:6-8)
bind 0.0.0.0             # <-- Listens on ALL interfaces
port 6379
protected-mode no         # <-- No protection at all
# requirepass ...         # <-- Commented out
```

**Solution:**
```conf
# FIXED (redis.conf)
bind 127.0.0.1            # Only localhost (or Docker network IP)
port 6379
protected-mode yes

# Set a strong password
requirepass YOUR_STRONG_REDIS_PASSWORD_HERE
```

Then update all connection URLs to include the password:
```python
# config.py
REDIS_URL: str = "redis://:YOUR_STRONG_REDIS_PASSWORD_HERE@127.0.0.1:6379/0"
CELERY_BROKER_URL: str = "redis://:YOUR_STRONG_REDIS_PASSWORD_HERE@127.0.0.1:6379/1"
```

In `docker-compose.yml`, stop exposing port 6379 to the host:
```yaml
# REMOVE this line from docker-compose.yml
# ports:
#   - "6379:6379"

# KEEP only the internal network — other containers can still reach Redis
```

---

### 3.5 — Flower Dashboard Credentials Hardcoded

| | |
|---|---|
| **File** | `docker-compose.yml:101` |
| **Impact** | Credentials visible in version control. Flower provides full task queue visibility and control |
| **Category** | Security |

**Problem:**
```yaml
# CURRENT (docker-compose.yml:101)
command: celery -A app.tasks.celery_app flower --basic_auth=admin:talkking_flower_pass
```

**Solution:**
```yaml
# FIXED — move to .env
command: celery -A app.tasks.celery_app flower --basic_auth=${FLOWER_USER}:${FLOWER_PASSWORD}
```

```env
# .env
FLOWER_USER=admin
FLOWER_PASSWORD=a_strong_random_password_here
```

---

### 3.6 — Celery Task Silently Loses Results When DB Storage Fails

| | |
|---|---|
| **File** | `app/tasks/analysis.py:59-67` |
| **Impact** | If the Supabase insert fails, the AI analysis results are lost forever. The task returns `{"status": "completed"}` but the client gets 404 when polling for feedback |
| **Category** | Reliability |

**Problem:**
```python
# CURRENT (analysis.py:59-67)
try:
    supabase.table("feedback_reports").insert(feedback).execute()
    supabase.table("sessions").update(
        {"status": "completed"}
    ).eq("id", session_id).execute()
except Exception as db_err:
    logger.warning(f"Supabase storage failed (non-fatal): {db_err}")
    # ^^ Results are LOST — task still returns "completed"
```

**Solution:**
```python
# FIXED — DB failure should mark session as failed, not silently succeed
try:
    supabase.table("feedback_reports").insert(feedback).execute()
    supabase.table("sessions").update(
        {"status": "completed"}
    ).eq("id", session_id).execute()
except Exception as db_err:
    logger.error("Supabase storage failed: %s", db_err)
    # Mark session as failed so the client knows
    try:
        supabase.table("sessions").update(
            {"status": "failed", "error": "Results could not be saved. Please try again."}
        ).eq("id", session_id).execute()
    except Exception:
        pass
    raise  # Re-raise to trigger Celery retry
```

---

## 4. MEDIUM Severity Issues

### 4.1 — Security Issues

#### 4.1.1 — CORS Overly Permissive

| | |
|---|---|
| **File** | `app/main.py:48-49` |

**Problem:**
```python
allow_methods=["*"],   # Allows DELETE, PUT, TRACE, etc.
allow_headers=["*"],   # Allows any header
```

**Solution:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)
```

---

#### 4.1.2 — OAuth `redirect_to` Open Redirect Vulnerability

| | |
|---|---|
| **File** | `app/api/v1/auth.py:170-178` |

**Problem:** The `redirect_to` query parameter is not validated. An attacker can craft a URL like `/auth/oauth/google?redirect_to=https://evil.com/steal-token` and Supabase will redirect there with tokens.

**Solution:**
```python
# Add at the top of auth.py
ALLOWED_REDIRECT_HOSTS = {"talkking.me", "www.talkking.me", "localhost"}

def _validate_redirect_url(url: str | None) -> str:
    """Validate redirect URL against allowlist."""
    if not url:
        return f"{_DEFAULT_REDIRECT}/auth/callback"
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_REDIRECT_HOSTS:
        raise HTTPException(status_code=400, detail="Invalid redirect URL")
    return url

# Then in oauth_login:
final_redirect = _validate_redirect_url(redirect_to)
```

---

#### 4.1.3 — XSS in Email HTML Templates

| | |
|---|---|
| **File** | `app/services/email_service.py:34` |

**Problem:** `user_name` is interpolated directly into HTML. If a user sets their name to `<script>alert('xss')</script>`, it renders in the email.

**Solution:**
```python
# FIXED — add html.escape
import html

async def send_feedback_email(
    to_email: str,
    user_name: str,
    overall_score: int,
    top_strength: str,
    top_improvement: str,
) -> None:
    safe_name = html.escape(user_name)
    safe_strength = html.escape(top_strength)
    safe_improvement = html.escape(top_improvement)
    # Use safe_name, safe_strength, safe_improvement in the HTML template
```

---

#### 4.1.4 — No Application-Level Rate Limiting on Auth Endpoints

| | |
|---|---|
| **File** | `app/api/v1/auth.py` |

**Problem:** Rate limiting relies entirely on Nginx. If someone accesses port 8000 directly (bypassing Nginx), there is no rate limiting on signup/login.

**Solution — Add a reusable rate-limit dependency:**
```python
# app/core/rate_limit.py
from fastapi import HTTPException, Request
from app.core.redis_client import get_redis_pool

async def rate_limit(request: Request, key_prefix: str, limit: int, window: int):
    """Reusable rate limiter using Redis."""
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    rate_key = f"{key_prefix}:{client_ip}"
    try:
        redis = get_redis_pool()
        count = await redis.incr(rate_key)
        if count == 1:
            await redis.expire(rate_key, window)
        if count > limit:
            raise HTTPException(status_code=429, detail="Too many requests. Please slow down.")
    except HTTPException:
        raise
    except Exception:
        pass  # Allow if Redis is down

# Usage in auth.py:
@router.post("/signup")
async def signup(body: SignupRequest, request: Request):
    await rate_limit(request, "signup", limit=5, window=3600)
    # ... rest of handler

@router.post("/login")
async def login(body: LoginRequest, request: Request):
    await rate_limit(request, "login", limit=10, window=300)
    # ... rest of handler
```

---

#### 4.1.5 — No Security Headers at Application Level

| | |
|---|---|
| **File** | `app/main.py` |

**Problem:** Security headers are only set by Nginx. If the app is accessed directly, no headers are set.

**Solution:**
```python
# Add to app/main.py after CORS middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

---

### 4.2 — Reliability Issues

#### 4.2.1 — Config Keys Default to Empty String (Silent Runtime Failures)

| | |
|---|---|
| **File** | `app/config.py:11-19` |

**Problem:** `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, and all AI API keys default to `""`. The app starts fine but fails at runtime with opaque errors.

**Solution — Add a startup validator:**
```python
# config.py — add after Settings class
from pydantic import model_validator

class Settings(BaseSettings):
    # ... existing fields ...

    @model_validator(mode="after")
    def validate_required_keys(self) -> "Settings":
        """Fail fast on missing critical configuration."""
        required = {
            "SUPABASE_URL": self.SUPABASE_URL,
            "SUPABASE_SERVICE_KEY": self.SUPABASE_SERVICE_KEY,
            "SUPABASE_JWT_SECRET": self.SUPABASE_JWT_SECRET,
        }
        missing = [k for k, v in required.items() if not v]
        if missing and self.ENVIRONMENT != "development":
            raise ValueError(f"Missing required config in {self.ENVIRONMENT}: {', '.join(missing)}")
        return self
```

---

#### 4.2.2 — No Error Handling in AI Orchestrator `asyncio.gather`

| | |
|---|---|
| **File** | `app/services/ai_orchestrator.py:37-40` |

**Problem:** If either Groq or Hume fails, the entire `asyncio.gather` raises and both results are lost. The other successful result is discarded.

**Solution:**
```python
# FIXED — use return_exceptions=True for partial results
import logging

logger = logging.getLogger(__name__)

async def analyze_recording(audio_bytes, user_mission, session_id, duration_seconds=300.0):
    # Phase 1: Parallel — allow partial failures
    results = await asyncio.gather(
        transcribe_audio(audio_bytes, duration_seconds=duration_seconds),
        analyze_acoustics(audio_bytes),
        return_exceptions=True,
    )

    # Handle partial failures gracefully
    transcript_result = results[0]
    acoustic_result = results[1]

    if isinstance(transcript_result, Exception):
        logger.error("Transcription failed: %s", transcript_result)
        transcript_result = TranscriptResult(text="", wpm=0, duration_seconds=duration_seconds)

    if isinstance(acoustic_result, Exception):
        logger.error("Acoustics analysis failed: %s", acoustic_result)
        acoustic_result = AcousticsResult(score=50, feedback="Vocal analysis unavailable.")

    del audio_bytes  # Free memory

    # Phase 2 and 3 continue as before...
```

---

#### 4.2.3 — Race Condition in `update_best_score`

| | |
|---|---|
| **File** | `app/services/user_service.py:61-70` |

**Problem:** Two concurrent requests can both read the old `best_score` and both try to update. The second update may overwrite the first with a lower score.

```python
# CURRENT — read-then-write race condition
profile = await get_user_profile(user_id)
if profile and score > profile.get("best_score", 0):
    supabase.table("profiles").update({"best_score": score}).eq("id", user_id).execute()
```

**Solution — Use a single atomic Supabase RPC or filter:**
```python
# FIXED — atomic update using a conditional filter
async def update_best_score(user_id: str, score: int) -> None:
    """Atomically update best_score only if the new score is higher."""
    supabase = get_supabase()
    await asyncio.to_thread(
        lambda: supabase.table("profiles")
            .update({"best_score": score})
            .eq("id", user_id)
            .lt("best_score", score)   # <-- Only update if current < new
            .execute()
    )
```

Or create a Supabase RPC function:
```sql
-- In Supabase SQL editor
CREATE OR REPLACE FUNCTION update_best_score(user_id_input UUID, new_score INT)
RETURNS VOID AS $$
BEGIN
  UPDATE profiles
  SET best_score = GREATEST(best_score, new_score)
  WHERE id = user_id_input;
END;
$$ LANGUAGE plpgsql;
```

---

#### 4.2.4 — `increment_sessions` RPC Has No Error Handling

| | |
|---|---|
| **File** | `app/services/user_service.py:53-58` |

**Solution:**
```python
async def increment_session_count(user_id: str) -> None:
    """Increment the user's total_sessions counter."""
    try:
        supabase = get_supabase()
        await asyncio.to_thread(
            lambda: supabase.rpc("increment_sessions", {"user_id_input": user_id}).execute()
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to increment session count for %s: %s", user_id, e)
```

---

#### 4.2.5 — Gemini `.format()` Crashes on Curly Braces in Transcript

| | |
|---|---|
| **File** | `app/services/gemini_service.py:58` |

**Problem:** If a transcript contains `{` or `}`, Python's `.format()` raises `KeyError` or `ValueError`.

**Solution:**
```python
# FIXED — use safe string substitution
prompt = BOLDNESS_PROMPT.replace("{transcript}", transcript).replace("{mission}", mission)
```

Or change the prompt template to use `$transcript` and `$mission` placeholders with `string.Template`.

---

#### 4.2.6 — Gemini Returns Score 0 for Empty Transcript (Penalizes Overall)

| | |
|---|---|
| **File** | `app/services/gemini_service.py:55-56` |

**Problem:** An empty transcript gets `score=0`, which heavily penalizes the overall score via the weighted average. Should return a neutral 50.

**Solution:**
```python
if not transcript.strip():
    return BoldnessResult(score=50, feedback="No speech detected for boldness analysis.")
```

---

#### 4.2.7 — No Pagination on Progress Endpoint

| | |
|---|---|
| **File** | `app/api/v1/progress.py:20-24` |

**Problem:** Returns ALL feedback reports for a user in one response. A user with 1000+ sessions will get a massive payload.

**Solution:**
```python
@router.get("/progress")
async def get_progress(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
):
    # ... add .limit(limit).order("created_at", desc=True) to the query
```

---

#### 4.2.8 — Session `duration` Field Has No Bounds

| | |
|---|---|
| **File** | `app/api/v1/sessions.py:20` |

**Problem:** `duration: int` accepts any value including `-1` or `999999999`.

**Solution:**
```python
from pydantic import Field

class CreateSessionRequest(BaseModel):
    type: Literal["video", "audio"]
    prompt_type: Literal["random", "specific", "free-flow"]
    prompt: str = Field(default="", max_length=2000)
    duration: int = Field(ge=1, le=3600)  # 1 second to 1 hour
```

---

#### 4.2.9 — Hume httpx Timeout May Be Insufficient

| | |
|---|---|
| **File** | `app/services/hume_service.py:102` |

**Problem:** Single `httpx.AsyncClient(timeout=60.0)` is shared across job creation, polling (up to 50s), and prediction fetch. The total may exceed 60s.

**Solution:**
```python
async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
    # ... or use separate clients for each phase
```

---

#### 4.2.10 — Groq Service Has No Error Handling on HTTP Call

| | |
|---|---|
| **File** | `app/services/groq_service.py:75-83` |

**Problem:** `response.raise_for_status()` raises `httpx.HTTPStatusError` with no catch.

**Solution:**
```python
async def transcribe_audio(audio_bytes: bytes, duration_seconds: float = 300.0) -> TranscriptResult:
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
                files={"file": ("audio.webm", audio_bytes, "audio/webm")},
                data={"model": "whisper-large-v3", "language": "en"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error("Groq API error (%s): %s", e.response.status_code, e.response.text[:200])
        return TranscriptResult(text="", wpm=0, duration_seconds=duration_seconds)
    except httpx.RequestError as e:
        logger.error("Groq connection error: %s", e)
        return TranscriptResult(text="", wpm=0, duration_seconds=duration_seconds)

    text = data.get("text", "")
    return TranscriptResult(
        text=text,
        filler_words=_count_filler_words(text),
        weak_phrases=_count_weak_phrases(text),
        wpm=_calculate_wpm(text, duration_seconds),
        duration_seconds=duration_seconds,
    )
```

---

#### 4.2.11 — Base64 Audio Encoding Inflates Celery Payload by 33%

| | |
|---|---|
| **File** | `app/api/v1/sessions.py:103` |

**Problem:** A 25MB audio file becomes ~33MB when base64-encoded and sent through Redis.

**Solution (long-term):** Store the audio in Supabase Storage first, then pass only the storage URL to the Celery task:
```python
# In sessions.py — upload to Supabase Storage
storage_path = f"recordings/{session_id}.webm"
supabase.storage.from_("audio").upload(storage_path, audio_bytes)

# Pass URL to Celery instead of raw bytes
task = process_recording.delay(
    audio_storage_path=storage_path,
    # ... other args
)

# In analysis.py — download from storage
audio_data = supabase.storage.from_("audio").download(audio_storage_path)
```

---

#### 4.2.12 — No SQL Migration Files in Repository

| | |
|---|---|
| **Location** | Project root |

**Problem:** Schema changes are managed via the Supabase dashboard. No version control for DB schema.

**Solution:** Use Supabase CLI migrations:
```bash
supabase init
supabase db pull          # Pull current schema
supabase migration new add_indexes
# Edit the migration SQL
supabase db push          # Apply to remote
```

---

### 4.3 — Code Quality Issues

#### 4.3.1 — Module-Level Logging Import Inside Function Bodies

| | |
|---|---|
| **Files** | `auth.py:91,113,145,224,236`, `gemini_service.py:93`, `hume_service.py:95` |

**Problem:** `import logging; logging.getLogger(__name__)` is called inside exception handlers, creating a new logger instance on every error.

**Solution:** Move to module level in each file:
```python
# At the top of each file
import logging
logger = logging.getLogger(__name__)

# Then in exception handlers use:
logger.warning("Signup failed: %s", e)
```

---

#### 4.3.2 — Default `mission` and `weakness` Hardcoded in 3 Places

| | |
|---|---|
| **Files** | `auth.py:82-83`, `auth.py:213-214`, `sessions.py:104` |

**Solution — Define constants:**
```python
# app/core/constants.py
DEFAULT_MISSION = "tech-interview"
DEFAULT_WEAKNESS = "filler-words"
DEFAULT_DURATION = 300.0
MAX_AUDIO_MB = 25
DEMO_MAX_AUDIO_MB = 10
```

Then import and use throughout the codebase.

---

#### 4.3.3 — Untyped `list[dict]` in Schemas

| | |
|---|---|
| **Files** | `app/schemas/feedback.py:12,37`, `app/schemas/assessment.py:50-51` |

**Problem:** `filler_words: list[dict]` and `weak_phrases: list[dict]` lose type safety and produce poor OpenAPI docs.

**Solution:**
```python
# In schemas/feedback.py
class FillerWordCount(BaseModel):
    word: str
    count: int

class WeakPhraseCount(BaseModel):
    phrase: str
    count: int

class ClarityDimension(BaseModel):
    score: int
    filler_words: list[FillerWordCount] = []   # Was list[dict]
    weak_phrases: list[WeakPhraseCount] = []   # Was list[dict]
    wpm: int = 0
    feedback: str = ""
```

---

#### 4.3.4 — Filler Word Detection Uses Substring Matching

| | |
|---|---|
| **File** | `app/services/groq_service.py:30-38` |

**Problem:** `text_lower.count("so")` matches inside words like "also", "somebody", "reason".

**Solution:**
```python
import re

def _count_filler_words(text: str) -> list[dict]:
    """Count filler words using word-boundary-aware matching."""
    text_lower = text.lower()
    results = []
    for filler in FILLER_WORDS:
        # Use word boundaries to avoid matching inside other words
        pattern = r"\b" + re.escape(filler) + r"\b"
        count = len(re.findall(pattern, text_lower))
        if count > 0:
            results.append({"word": filler, "count": count})
    return sorted(results, key=lambda x: x["count"], reverse=True)
```

---

#### 4.3.5 — Localhost Origins in Default CORS List

| | |
|---|---|
| **File** | `app/config.py:28-33` |

**Problem:** If `CORS_ORIGINS` is not set in `.env`, localhost origins are allowed in production.

**Solution:**
```python
# config.py — make defaults environment-aware
@property
def effective_cors_origins(self) -> list[str]:
    if self.ENVIRONMENT == "development":
        return self.CORS_ORIGINS  # includes localhost
    return [o for o in self.CORS_ORIGINS if "localhost" not in o]
```

Or better: ensure production `.env` always explicitly sets `CORS_ORIGINS`.

---

#### 4.3.6 — Duplicate `CMD` in Dockerfile

| | |
|---|---|
| **File** | `Dockerfile:52` and `Dockerfile:62-67` |

**Problem:** Two `CMD` instructions. Only the last one runs. The first is dead code.

**Solution:** Remove the first `CMD` at line 52.

---

## 5. LOW Severity Issues

### 5.1 — Magic Numbers Throughout Codebase

| File | Line | Magic Number | Suggested Constant |
|------|------|--------------|---------------------|
| `sessions.py:88` | `300` | Default duration fallback | `DEFAULT_DURATION_SECONDS = 300` |
| `feedback_engine.py:14` | `85` | Base clarity score | `BASE_CLARITY_SCORE = 85` |
| `hume_service.py:37` | `50` | Neutral vocal score | `NEUTRAL_SCORE = 50` |
| `assessment.py:13` | `5` | Demo rate limit | `DEMO_RATE_LIMIT = 5` |
| `assessment.py:14` | `3600` | Rate window seconds | `DEMO_RATE_WINDOW = 3600` |

**Solution:** Create `app/core/constants.py` and collect all magic numbers there.

---

### 5.2 — Ad-hoc Test Scripts with Hardcoded Credentials

| Files | Issue |
|-------|-------|
| `test_signup.py`, `test_login.py`, `test_me.py`, `test_hume.py`, `test_run.py`, `force_user.py` | Contain hardcoded email/password and sit in root directory |

**Solution:**
1. Move to a `scripts/` directory
2. Use environment variables instead of hardcoded credentials
3. Add `scripts/` to `.gitignore` or convert to proper pytest fixtures

---

### 5.3 — Debug Artifacts in Root Directory

| Files |
|-------|
| `curl_log.txt`, `error.txt`, `response.txt`, `server_log.txt`, `test.wav` |

**Solution:** Delete them and add to `.gitignore`:
```gitignore
*.txt
!requirements*.txt
test.wav
```

---

### 5.4 — `joined_at` and `recorded_at` as Strings Instead of `datetime`

| Files | Lines |
|-------|-------|
| `app/schemas/user.py:46` | `joined_at: Optional[str]` |
| `app/schemas/session.py:18` | `recorded_at: Optional[str]` |

**Solution:**
```python
from datetime import datetime

joined_at: Optional[datetime] = None
recorded_at: Optional[datetime] = None
```

---

### 5.5 — Unused `Achievement` Schema

| File | `app/schemas/achievement.py` |
|------|------|

The `Achievement` model is defined but never imported or used anywhere. Either implement the achievements feature or remove the dead code.

---

### 5.6 — Unused `pydub` Dependency

| File | `requirements.txt` |
|------|-----|

`pydub` is listed but never imported. Remove it to reduce image size, or use it for accurate audio duration calculation instead of the bitrate-based estimate in `audio_utils.py`.

---

### 5.7 — Nginx Docs Location Regex Doesn't Match

| File | `infra/nginx/nginx.conf:136` |
|------|------|

The regex `^/(docs|redoc|openapi.json)` doesn't match the actual docs paths `/api/docs` and `/api/redoc`. Either fix the regex or remove the block since docs are handled by the general `/api/` location.

---

### 5.8 — F-Strings in Logger Calls

| Files | `analysis.py:67,80,98` |
|-------|------|

**Problem:** `logger.warning(f"...")` evaluates the string even if WARNING level is disabled.

**Solution:** Use lazy formatting:
```python
# BAD
logger.warning(f"Supabase storage failed: {db_err}")

# GOOD
logger.warning("Supabase storage failed: %s", db_err)
```

---

### 5.9 — Hume `vocal_fry` and `raspiness` Always `False`

| File | `app/services/hume_service.py:185-186` |
|------|------|

These fields are never populated with real data. Either remove them from the `AcousticsResult` dataclass or document that they are planned features. They mislead frontend developers into thinking the data is real.

---

### 5.10 — History Endpoint Has No `response_model`

| File | `app/api/v1/history.py:10` |
|------|------|

The response shape is not validated or documented in OpenAPI. Add a `HistoryResponse` Pydantic model.

---

## 6. Testing Gaps

### Current Test Coverage

| Test File | Tests | What's Covered |
|-----------|-------|----------------|
| `test_health.py` | 5 | Health endpoint, CORS, docs |
| `test_routes.py` | 9 | Route existence, auth guards |
| `test_core.py` | 4 | Custom exceptions |
| `test_schemas.py` | 11 | All Pydantic schemas |
| `test_ai_services.py` | 7 | Groq, Gemini, Hume (HTTP mocked) |
| `test_tasks.py` | 4 | Celery config and registration |
| `test_email.py` | 2 | Mailgun email (mocked) |
| `test_orchestrator.py` | 5 | Feedback engine, orchestrator |
| **Total** | **47** | |

### Missing Tests (Priority Order)

| Priority | Missing Test | Why It Matters |
|----------|-------------|----------------|
| **HIGH** | Auth flow integration (signup -> login -> use token -> access protected route) | The most critical user journey is untested end-to-end |
| **HIGH** | Assessment rate limiting (verify 429 on 6th request, verify reset after window) | Rate limiting logic is complex and untested |
| **HIGH** | Negative input tests (empty password signup, huge payload, invalid file type) | No adversarial testing |
| **MEDIUM** | `user_service.py` unit tests (get/update profile, increment sessions, best score) | Core CRUD untested |
| **MEDIUM** | Celery `process_recording` end-to-end with mocked services | The full pipeline is untested |
| **MEDIUM** | Audio upload size validation (exact boundary: 25MB - 1 byte passes, 25MB + 1 byte fails) | Edge cases untested |
| **LOW** | `progress.py` data transformation (score averaging, dimension extraction) | Complex data logic untested |
| **LOW** | Hume polling loop (test all states: COMPLETED, FAILED, timeout) | Only fallback path is tested |
| **LOW** | OAuth code exchange with invalid/expired code | Error paths untested |

### Recommended Test Additions

```python
# tests/test_auth_flow.py — Integration test
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_signup_rejects_weak_password(client: AsyncClient):
    """Password < 8 chars should be rejected."""
    response = await client.post("/api/v1/auth/signup", json={
        "email": "test@example.com",
        "password": "123",
        "name": "Test User",
    })
    assert response.status_code == 422  # Pydantic validation error

@pytest.mark.asyncio
async def test_signup_rejects_empty_name(client: AsyncClient):
    response = await client.post("/api/v1/auth/signup", json={
        "email": "test@example.com",
        "password": "Str0ngP@ss!",
        "name": "",
    })
    assert response.status_code == 422


# tests/test_rate_limiting.py
@pytest.mark.asyncio
async def test_demo_rate_limit_blocks_after_5(client: AsyncClient, mock_redis):
    """6th demo request within 1 hour should get 429."""
    for i in range(5):
        response = await client.post("/api/v1/demo/assess", files={"audio": b"fake"})
        assert response.status_code != 429

    response = await client.post("/api/v1/demo/assess", files={"audio": b"fake"})
    assert response.status_code == 429


# tests/conftest.py — Add shared fixtures
@pytest.fixture
async def authenticated_client(client: AsyncClient):
    """Client with a valid JWT token."""
    # ... mock JWT or create a test user
    client.headers["Authorization"] = f"Bearer {test_token}"
    return client
```

---

## 7. Missing Best Practices

### 7.1 — Global Exception Handler (HIGH)

**Why:** Without this, unexpected exceptions return raw Python tracebacks to the client (in debug mode) or generic 500s with no structured body.

```python
# app/core/exception_handlers.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred. Please try again later.",
                "type": "internal_error",
            },
        )

# In main.py:
from app.core.exception_handlers import register_exception_handlers
register_exception_handlers(app)
```

---

### 7.2 — Request/Response Logging Middleware (HIGH)

**Why:** Without this, there is no way to trace a request through the system for debugging.

```python
# app/core/logging_middleware.py
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("talkking.access")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %s %.0fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

# In main.py:
app.add_middleware(RequestLoggingMiddleware)
```

---

### 7.3 — Request Timeout Middleware (MEDIUM)

**Why:** A slow downstream service can block a request indefinitely, holding a worker hostage.

```python
# app/core/timeout_middleware.py
import asyncio
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout: float = 60.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Request timed out")

# In main.py:
app.add_middleware(TimeoutMiddleware, timeout=60.0)
```

---

### 7.4 — Structured Logging (MEDIUM)

**Why:** Plain-text logs are hard to parse in production monitoring tools (Datadog, CloudWatch, ELK).

```python
# app/core/logging_config.py
import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        })

def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)

# Call in main.py before app creation:
from app.core.logging_config import configure_logging
configure_logging()
```

---

### 7.5 — OpenAPI Error Response Models (MEDIUM)

**Why:** API docs only show success responses. Frontend developers don't know what error shapes to expect.

```python
# app/schemas/errors.py
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    detail: str

class ValidationErrorResponse(BaseModel):
    detail: list[dict]

# Usage in routes:
@router.post(
    "/signup",
    response_model=AuthResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Signup failed"},
        422: {"model": ValidationErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Rate limited"},
    },
)
async def signup(body: SignupRequest):
    ...
```

---

## 8. Phased Action Plan

### Phase 1: Critical & Security (Do Immediately -- Day 1)

- [ ] **Rotate ALL secrets** in `.env` (Supabase, Groq, Gemini, Hume, Sentry, Datadog)
- [ ] **Verify git history** for committed secrets and purge if found
- [ ] **Enable Redis authentication** (`requirepass`, `protected-mode yes`, `bind 127.0.0.1`)
- [ ] **Move Flower credentials** from `docker-compose.yml` to `.env`
- [ ] **Remove Redis port exposure** from `docker-compose.yml`
- [ ] **Add password validation** to `SignupRequest` (min 8 chars, complexity)
- [ ] **Validate OAuth `redirect_to`** against an allowlist of trusted hosts

### Phase 2: High-Priority Reliability (Days 2-3)

- [ ] **Stream audio uploads** with size cap before reading into memory
- [ ] **Add timeout to demo assessment** endpoint (`asyncio.wait_for`)
- [ ] **Fix Celery task** to mark session "failed" when DB storage fails
- [ ] **Add `return_exceptions=True`** to `asyncio.gather` in AI orchestrator
- [ ] **Fix `update_best_score` race condition** with atomic DB update
- [ ] **Add global exception handler** middleware
- [ ] **Add request logging** middleware

### Phase 3: Medium-Priority Improvements (Week 1-2)

- [ ] **Restrict CORS** methods/headers to actual values
- [ ] **Add security headers** middleware at application level
- [ ] **HTML-escape user inputs** in email templates
- [ ] **Add application-level rate limiting** on auth endpoints
- [ ] **Add startup config validator** (fail fast on missing keys in production)
- [ ] **Fix filler word detection** to use word-boundary regex (`\b`)
- [ ] **Fix Gemini `.format()` crash** on curly braces in transcript
- [ ] **Fix Gemini empty transcript** to return neutral score (50, not 0)
- [ ] **Add error handling** to Groq HTTP call
- [ ] **Increase Hume httpx timeout** to 120s
- [ ] **Add bounds to `duration` field** (`ge=1, le=3600`) and `prompt` field (`max_length=2000`)
- [ ] **Add pagination** to progress endpoint
- [ ] **Type `list[dict]`** to proper Pydantic models in schemas
- [ ] **Move `import logging`** to module level in all files
- [ ] **Extract constants** for hardcoded defaults (mission, weakness, duration)
- [ ] **Set up Supabase CLI migrations** for schema version control

### Phase 4: Polish & Cleanup (Week 2-3)

- [ ] **Delete debug artifacts** (`curl_log.txt`, `error.txt`, `response.txt`, `server_log.txt`, `test.wav`)
- [ ] **Move ad-hoc scripts** to `scripts/` directory with env-var-based config
- [ ] **Remove duplicate `CMD`** from Dockerfile
- [ ] **Remove unused `pydub`** from `requirements.txt` (or use it for audio duration)
- [ ] **Remove or implement `Achievement` schema**
- [ ] **Fix Nginx docs location** regex to match actual paths
- [ ] **Replace f-strings** in logger calls with lazy `%s` formatting
- [ ] **Add `response_model`** to history endpoint
- [ ] **Change `joined_at`/`recorded_at`** from `str` to `datetime`
- [ ] **Document `vocal_fry`/`raspiness`** as unimplemented or remove from schema
- [ ] **Add structured JSON logging**
- [ ] **Add request timeout middleware**
- [ ] **Add OpenAPI error response models** to all endpoints
- [ ] **Write missing tests**: auth flow, rate limiting, user service, negative inputs, Celery pipeline

### Phase 5: Testing (Ongoing)

- [ ] **Write auth flow integration tests** (signup -> login -> access protected route)
- [ ] **Write rate limiting tests** (verify 429, verify window reset)
- [ ] **Write negative input tests** (empty password, huge payload, bad file type)
- [ ] **Write user_service unit tests** (get/update profile, increment, best score)
- [ ] **Write Celery pipeline end-to-end test** (mocked services)
- [ ] **Write audio size boundary tests** (exact limit edge cases)
- [ ] **Write progress data transformation tests**
- [ ] **Write Hume polling loop tests** (all states)
- [ ] **Add shared fixtures** to `conftest.py` (authenticated client, mock DB)
- [ ] **Set up CI** to run tests on every push

---

## Summary

The TalkKing backend has a **solid architectural foundation** with clean separation of concerns, proper async patterns, and thoughtful AI orchestration. The main areas needing immediate attention are:

1. **Secret management** -- rotate exposed keys, enable Redis auth
2. **Input validation** -- password strength, audio streaming, field bounds
3. **Error resilience** -- handle partial AI failures, fix Celery result loss
4. **Defense in depth** -- add app-level rate limiting, security headers, CORS restrictions
5. **Test coverage** -- add integration tests for critical flows

Addressing the Phase 1 and Phase 2 items will significantly harden the backend for production use. Phase 3-5 items are improvements that elevate the codebase from "functional" to "production-grade."
