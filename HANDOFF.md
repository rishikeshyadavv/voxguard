# HANDOFF — Step 0 Complete

## 1. Completed Tasks & Green Tests
- **Backend Scaffold**:
  - `backend/pyproject.toml` configured with Python 3.11, FastAPI, Uvicorn, NumPy, Soxr, SoundFile, HTTPX, Ruff, Mypy, Pytest, and Pytest-asyncio.
  - `backend/app/main.py` implementing `GET /health` returning `{"status": "ok", "model_version": "stub"}` with CORS middleware.
  - `backend/tests/unit/test_health.py` unit test verifying `/health`.
  - `backend/tests/integration/test_health_integration.py` integration test verifying async client interaction with `/health`.
  - Type checking (`mypy app`), linting (`ruff check .`), and formatting (`ruff format --check .`) pass with 0 warnings/errors.
- **Frontend Scaffold**:
  - `frontend/` initialized with Vite, React 18, TypeScript (strict mode), and Tailwind CSS.
  - Base `App.tsx` component with header, backend health status badge, live telemetry section placeholder, and file dropzone placeholder.
  - `frontend/src/App.test.tsx` Vitest test verifying rendering and health check integration.
  - Linting (`eslint`), typechecking (`tsc --noEmit`), unit test (`vitest --run`), and production build (`vite build`) all pass.
- **Containerization & CI**:
  - `backend/Dockerfile` with Python 3.11-slim, `libsndfile1`, and `uv`.
  - `frontend/Dockerfile` multi-stage build with `nginx:alpine` and proxy config for `/health`, `/api`, and `/ws`.
  - `docker-compose.yml` linking backend (port 8000) and frontend (port 3000).
  - `.github/workflows/ci.yml` running backend lint/typecheck/test and frontend lint/typecheck/test/build on PRs and pushes to `main` and `master`.

## 2. Active Failing Tests or Unfinished Files
- None. All unit, integration, lint, and build checks are green.

## 3. Commands to Run and Verify
- **Backend**:
  ```bash
  cd backend
  ruff check .
  ruff format --check .
  mypy app
  pytest -v
  ```
- **Frontend**:
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm test -- --run
  npm run build
  ```
- **Make Target (Linux/macOS/WSL)**:
  ```bash
  make lint
  make test
  ```

## 4. Next Step Prompt
```markdown
Read AGENTS.md, docs/PROTOTYPE.md, and HANDOFF.md. Execute Step 1 (Audio core):
Implement backend/app/audio: a RingBuffer holding up to 30 s of float32 16 kHz audio, a Windower that yields 2.0 s windows every 0.5 s with correct overlap and carry-over of partial data, and io.py that decodes PCM16 bytes and loads uploaded wav/mp3/flac files to 16 kHz mono float32 (resample with soxr). Write unit tests first, including odd chunk sizes, exact window counts, and buffer cap.
```
