# HANDOFF — Step 6 Complete

## 1. Completed Tasks & Green Tests
- **Dependencies & Configuration**:
  - Added `torch`, `torchaudio`, and `transformers` to [`backend/pyproject.toml`](file:///D:/projects/VOXGAURD/backend/pyproject.toml) and verified PyTorch CPU execution.
  - Added `hf_model_name` (default: `"MattyB95/AST-VOXCELEB-SPOOFING-HOTFIX"`) and `hf_device` (`"cpu"`) in [`backend/app/config.py`](file:///D:/projects/VOXGAURD/backend/app/config.py).
- **Hugging Face Inference Engine (`backend/app/inference/hf_engine.py`)**:
  - Implemented `HFEngine(InferenceEngine)`:
    - Conforms to `InferenceEngine` protocol with strict `validate_audio_window` checks (1D float32 16 kHz, 32,000 samples, no NaN/Infs).
    - Dynamic label resolution from `model.config.id2label` parsing spoof/fake vs. bonafide/real classes with softmax probability pooling.
    - Softmax probability mapping strictly bounded in $[0.0, 1.0]$.
    - `warmup()` executing zero-window dummy pass to initialize graph/memory.
    - Per-window latency profiling logging timing in milliseconds.
- **Factory Integration (`backend/app/inference/factory.py`)**:
  - `get_inference_engine`: Dynamically instantiates `HFEngine` when `MODEL_BACKEND="hf"` is requested with graceful fallback to `StubEngine` if model checkpoint is unavailable offline.
- **Benchmark Script (`backend/scripts/bench.py`)**:
  - Generates 10 test windows (silence, multi-frequency sine waves, Gaussian noise).
  - Evaluates engine over 10 iterations per window (100 total inferences).
  - Reports mean, median, p95, min, and max latencies.
  - Enforces $< 750$ ms CPU latency SLA.
- **Unit Tests (`backend/tests/unit/test_inference/`)**:
  - [`test_hf_engine.py`](file:///D:/projects/VOXGAURD/backend/tests/unit/test_inference/test_hf_engine.py): 7 tests covering protocol conformance, label index resolution (normal and inverted mappings), high-confidence spoof detection, high-confidence bonafide detection, warmup execution, and invalid window rejection.
  - [`test_factory.py`](file:///D:/projects/VOXGAURD/backend/tests/unit/test_inference/test_factory.py): 5 tests verifying stub selection, case insensitivity, mocked HF engine instantiation, fallback to stub on load error, and invalid backend name rejection.
- **Verification**:
  - `ruff check .` &rarr; 0 errors
  - `ruff format --check .` &rarr; clean
  - `mypy app` &rarr; 0 errors (strict mode across all 18 source files)
  - `pytest -v` (backend) &rarr; 67/67 tests passed
  - `npm test -- --run` (frontend) &rarr; 8/8 tests passed

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
- **Benchmark Execution**:
  ```bash
  python backend/scripts/bench.py --backend stub --threshold 750
  ```
- **Frontend Quality**:
  ```bash
  cd frontend
  npm run lint
  npm run typecheck
  npm test -- --run
  ```

## 4. Next Step Prompt (Step 7: Demo Data & Evaluation Pipeline)
```markdown
Read AGENTS.md, docs/PROTOTYPE.md, and HANDOFF.md. Execute Step 7 (Demo Data & Evaluation):
1. Setup demo audio directories:
   - demo/real/ and demo/fake/ with generated/synthesized evaluation clips (3+ clips each for demo testing, plus 10+ clips each for evaluation).
2. Implement backend/scripts/evaluate.py:
   - Evaluates all audio clips across demo/real/ and demo/fake/ using the inference engine.
   - Computes accuracy, mean fake score per class, and false-alarm rate at T_ALERT (0.75).
   - Generates docs/EVAL.md with formatted markdown evaluation report table.
3. Tests in backend/tests/unit/:
   - test_evaluate_script.py verifying evaluation metrics calculation.
4. Verify with ruff check, ruff format, mypy app, and pytest. Update HANDOFF.md and git commit as: feat(eval): add benchmark clips, evaluation script, and accuracy report (Step 7).
```
