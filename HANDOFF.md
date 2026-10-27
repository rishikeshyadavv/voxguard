# HANDOFF — Step 2 Complete

## 1. Completed Tasks & Green Tests
- **Config (`backend/app/config.py`)**:
  - Implemented `Settings` dataclass reading environment variables with defaults: `smooth_n=6`, `t_suspicious=0.5`, `t_alert=0.75`, `alert_consecutive=3`, `clear_threshold=0.4`, `sample_rate=16000`, `window_duration_seconds=2.0`, `hop_duration_seconds=0.5`, `model_backend="stub"`.
- **Decision Engine (`backend/app/decision/`)**:
  - `smoothing.py`: `ScoreSmoother` computing a moving average over the last $N$ window scores (defaults to 6 from config), correctly averaging partial windows (< N) and returning 0.0 when empty.
  - `state_machine.py`:
    - `CallState` enum (`NORMAL`, `SUSPICIOUS`, `ALERT`).
    - `StateUpdate` dataclass emitting current state, smoothed score, `alert_triggered` boolean, and consecutive alert counts.
    - `StateMachine` (and `DecisionEngine` alias) implementing hysteresis:
      - Transitions `NORMAL` -> `SUSPICIOUS` when `smoothed_score >= t_suspicious` (0.5).
      - Transitions to `ALERT` strictly when `smoothed_score >= t_alert` (0.75) for `consecutive_alert_count` (3) consecutive windows.
      - Returns to `NORMAL` strictly when `smoothed_score < clear_threshold` (0.4).
      - Emits `alert_triggered = True` on the initial window entering `ALERT` and stays quiet on subsequent alert windows.
      - Resets the active trigger cycle upon dropping back to `NORMAL`.
- **Unit & Property Tests (`backend/tests/unit/test_decision/`)**:
  - `test_smoothing.py`: 5 tests covering initial state, partial window means, FIFO overflow, reset, and parameter validation.
  - `test_state_machine.py`: 8 tests including:
    - Standard transitions (`NORMAL` -> `SUSPICIOUS` -> `ALERT` -> `NORMAL`).
    - Hysteresis retention (score in `[0.4, 0.49]` remains in `SUSPICIOUS`).
    - Consecutive count resets upon interruption (< 0.75).
    - Threshold ordering validation.
    - Hypothesis property test: `ALERT` is unreachable in fewer than `consecutive_alert_count` steps.
    - Hypothesis property test: Hysteresis holds—state cannot drop to `NORMAL` if score stays above `clear_threshold`.
    - Hypothesis property test: `alert_triggered` fires once per trigger cycle without alert spam.
- **Verification**:
  - Ruff check: 0 errors
  - Ruff format: clean
  - Mypy app: 0 errors (strict mode across all 10 source files)
  - Pytest: 37/37 tests passed (backend) + 1/1 test passed (frontend)

## 2. Active Failing Tests or Unfinished Files
- None. All test suites pass.

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
  ```

## 4. Next Step Prompt (Step 3: Inference Interface and Stub)
```markdown
Read AGENTS.md, docs/PROTOTYPE.md, and HANDOFF.md. Execute Step 3 (Inference Interface and Stub):
1. Implement backend/app/inference/:
   - base.py: Define the InferenceEngine Protocol with predict(window: np.ndarray) -> float (where window is float32 mono 16 kHz, returning p_fake in [0.0, 1.0]).
   - stub.py: Implement StubEngine returning deterministic p_fake (configurable mode: fixed score, linear ramp, or RMS-based pattern) to enable headless testing and UI integration without requiring heavy model checkpoints.
   - factory.py / get_engine(): Select engine implementation via MODEL_BACKEND env var ("stub", "hf", etc.).
2. Write unit tests in backend/tests/unit/test_inference/:
   - test_stub_engine.py verifying bounds [0.0, 1.0], deterministic outputs, input shape validation, and factory selection.
3. Verify with ruff check, ruff format, mypy app, and pytest. Update HANDOFF.md and git commit as: feat(inference): implement inference protocol and deterministic stub engine (Step 3).
```
