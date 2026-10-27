# HANDOFF — Step 3 Complete

## 1. Completed Tasks & Green Tests
- **Inference Interface & Protocol (`backend/app/inference/base.py`)**:
  - `InferenceEngine(Protocol)`: Decorated with `@runtime_checkable`, requiring `predict(window: np.ndarray) -> float`, `warmup() -> None`, `model_name: str`, and `version: str`.
  - `validate_audio_window`: Reusable validation checking 1D dimension, float32 dtype, non-empty, expected 32,000 samples (2.0s @ 16 kHz), and rejecting NaNs/Infs.
- **Deterministic Stub Engine (`backend/app/inference/stub.py`)**:
  - `StubEngine(InferenceEngine)`:
    - Default `"energy"` mode: Computes RMS of window; yields high fake probability (0.88) when $\text{RMS} \ge \text{threshold}$ (0.25) and low probability (0.12) on ambient silence/normal speech.
    - Controllable `"fixed"` mode: `set_fixed_score(score: float)` for deterministic integration and E2E test scenarios.
    - Controllable `"ramp"` mode: Monotonically cycles scores in $[0.0, 1.0]$.
    - Exposes `warmup()` and `reset()` operations.
- **Inference Engine Factory (`backend/app/inference/factory.py`)**:
  - `get_inference_engine(backend: Optional[str] = None)`: Instantiates the configured engine based on `MODEL_BACKEND` (case-insensitive "stub" default, raises informative `NotImplementedError` for "hf" reserved for Step 6, raises `ValueError` for unknown backend names).
- **Unit Tests (`backend/tests/unit/test_inference/`)**:
  - `test_stub_engine.py`: 8 tests verifying Protocol conformance (`isinstance`), strict input validation (types, shapes, dtypes, sample counts, NaNs, Infs), output score bounds in $[0.0, 1.0]$, energy mode discrimination, fixed mode, ramp mode, and warmup/reset.
  - `test_factory.py`: 4 tests verifying default stub loading, case-insensitive explicit loading, HF placeholder error, and unknown backend rejection.
- **Verification**:
  - Ruff check: 0 errors
  - Ruff format: clean
  - Mypy app: 0 errors (strict mode across all 14 source files)
  - Pytest: 49/49 tests passed (backend) + 1/1 test passed (frontend)

## 2. Active Failing Tests or Unfinished Files
- None. All test suites pass.

## 3. Commands to Run and Verify
- **Backend Quality**:
  ```bash
  cd backend
  ruff check .
  ruff format --check .
  mypy app
  pytest -v
  ```
- **Frontend Quality**:
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm test -- --run
  ```

## 4. Next Step Prompt (Step 4: API Layer)
```markdown
Read AGENTS.md, docs/PROTOTYPE.md, and HANDOFF.md. Execute Step 4 (API Layer):
1. Implement backend/app/api/:
   - predict.py: POST /api/v1/predict accepting multipart audio file (wav/mp3/flac/ogg), 10 MB payload cap, returning verdict ("real" | "suspicious" | "fake"), mean p_fake, per-window scores list, duration, and error handling (400 for empty or unparseable audio, 413 for payload > 10MB).
   - ws_mic.py: WebSocket /ws/mic accepting binary PCM16 audio frames (and optional initial sample_rate JSON config), orchestrating RingBuffer -> Windower -> InferenceEngine -> ScoreSmoother -> StateMachine, emitting JSON messages per schema (score, alert, error), and handling mid-stream client disconnect gracefully.
   - Include router mounts in backend/app/main.py.
2. Integration tests in backend/tests/integration/:
   - test_predict_api.py: Valid audio uploads (verdict, duration, window scores), empty file rejection, file size cap enforcement, and corrupt file rejection.
   - test_ws_mic.py: Full streaming lifecycle with chunked PCM16, verification of emitted score and alert JSON frames, irregular chunk streaming, and mid-stream disconnect cleanup.
3. Verify with ruff check, ruff format, mypy app, and pytest. Update HANDOFF.md and git commit as: feat(api): implement predict endpoint and streaming websocket (Step 4).
```
