# VoxGuard Prototype: Build Spec and Agent Playbook

A cut-down version of the full docs, for the first working prototype. Goal: **speak into the browser mic or upload a clip and see a live real-vs-AI verdict.** Everything else waits.

**Using agy CLI:** put this in `docs/PROTOTYPE.md` next to the full docs. Run one build step per session, paste the step's prompt, and commit when tests are green.

---

## 1. Prototype definition

### 1.1 Goal

Prove the core loop end to end: audio in -> windowed inference -> smoothed score -> live dashboard alert. Accuracy is secondary to a working pipeline; the model is swapped in behind an interface.

### 1.2 In scope

- Browser microphone streaming over WebSocket.
- Audio file upload with a verdict.
- 2 s windows, 0.5 s hop, 16 kHz mono.
- A pretrained anti-spoofing model (found on Hugging Face), or a stub model to unblock UI work.
- Smoothing plus a NORMAL / SUSPICIOUS / ALERT state machine.
- Dashboard: confidence meter, rolling chart, alert banner, upload box, demo-clip buttons.
- Docker compose, basic CI, core tests.

### 1.3 Out of scope (until prototype is done)

Twilio calls, SMS, saliency maps, telephony retraining, database, auth, deployment, call history.

### 1.4 Definition of done

| # | Check |
| --- | --- |
| 1 | `docker compose up` starts backend and frontend |
| 2 | Upload a real clip -> verdict "real"; upload a cloned clip -> verdict "fake" |
| 3 | Mic streaming updates the meter at least every 0.5-1 s |
| 4 | ALERT banner fires on a fake clip played into the mic, and stays quiet on real speech |
| 5 | Inference under about 500 ms per window on a laptop CPU |
| 6 | `make test` and CI are green |
| 7 | A short screen recording of the demo exists |

### 1.5 Time box

About 8-12 hours of focused work. If step 4 (real model) fights you for over 2 hours, keep the stub and move on; the UI and pipeline are worth more than a few accuracy points at this stage.

---

## 2. Prototype architecture

```
Browser mic (AudioWorklet, PCM16 16k)        File upload
        |  WS /ws/mic                              | POST /api/v1/predict
        v                                          v
   FastAPI  ->  RingBuffer -> Windower -> InferenceEngine -> Smoother/StateMachine
                                              (Stub | ONNX/HF)            |
                                                                          v
                                                WS /ws/dashboard (same session)
                                                                          |
                                                                   React dashboard
```

### 2.1 Decisions that keep it simple

- **Single process, in-memory sessions.** No database.
- **Same WebSocket for mic and results is fine**: the mic client sends binary PCM, the server replies with JSON on the same socket. Add `/ws/dashboard` later only if you need multiple viewers.
- **Inference interface** so the model can change without touching anything else:

```python
class InferenceEngine(Protocol):
    def predict(self, window: np.ndarray) -> float:  # float32 mono 16 kHz, returns p_fake in [0,1]
        ...
```

Implementations: `StubEngine` (deterministic, e.g. energy-based or file-name-driven), `HFEngine` (transformers pipeline), `OnnxEngine` (later).

- **Python 3.11**, FastAPI, uvicorn, numpy, soxr or scipy, soundfile, onnxruntime or transformers + torch (CPU).
- **Frontend:** Vite + React + TypeScript + Tailwind + Recharts.

### 2.2 Message schema (server -> client)

```json
{"type":"score","t":12.5,"p_fake":0.83,"p_smooth":0.71,"state":"SUSPICIOUS"}
{"type":"alert","t":14.0,"p_smooth":0.82}
{"type":"error","message":"..."}
```

Client -> server on `/ws/mic`: binary frames of little-endian PCM16 mono at 16 kHz (any chunk size). First text frame may carry `{"sample_rate":16000}`.

### 2.3 Decision logic defaults

`SMOOTH_N=6`, `T_SUSPICIOUS=0.5`, `T_ALERT=0.75`, `ALERT_CONSECUTIVE=3`, clear below 0.4. Keep these in `config.py` and env-overridable.

### 2.4 Repo layout (prototype)

```
voxguard/
  AGENTS.md  Makefile  docker-compose.yml
  docs/  (PROTOTYPE.md + full docs)
  backend/app/  main.py config.py
                audio/ (buffer.py, windowing.py, io.py)
                inference/ (base.py, stub.py, hf_engine.py)
                decision/ (smoothing.py, state_machine.py)
                api/ (predict.py, ws_mic.py)
  backend/tests/ (unit/, integration/, fixtures/)
  frontend/src/ (components/, hooks/useVoxSocket.ts, lib/)
  demo/real/  demo/fake/
```

---

## 3. Build plan with agy prompts

Run in order. Each step ends with tests passing and a commit.

### Step 0: Scaffold (30-45 min)

**Prompt:**

> Read docs/PROTOTYPE.md. Scaffold the repo per section 2.4: FastAPI backend with pyproject (ruff, mypy, pytest, pytest-asyncio, httpx), Vite React TS Tailwind frontend, Dockerfiles, docker-compose, a Makefile with `lint`, `test`, `up`, a `/health` endpoint, an AGENTS.md, and a GitHub Actions CI workflow that runs backend and frontend lint, tests and build. Add one passing test per side.

**Done when:** `make test` passes, `docker compose up` serves `/health` and a blank page.

### Step 1: Audio core (1-1.5 h)

**Prompt:**

> Implement backend/app/audio: a RingBuffer holding up to 30 s of float32 16 kHz audio, a Windower that yields 2.0 s windows every 0.5 s with correct overlap and carry-over of partial data, and io.py that decodes PCM16 bytes and loads uploaded wav/mp3/flac files to 16 kHz mono float32 (resample with soxr). Write unit tests first, including odd chunk sizes, exact window counts, and buffer cap.

### Step 2: Decision logic (45 min)

**Prompt:**

> Implement decision/smoothing.py (moving average over last N) and decision/state\_machine.py (NORMAL, SUSPICIOUS, ALERT with consecutive-window rule and hysteresis, thresholds from config). Use hypothesis tests to prove ALERT is never reached without the consecutive rule and that ALERT is emitted once per session.

### Step 3: Inference interface and stub (30 min)

**Prompt:**

> Add inference/base.py with the InferenceEngine Protocol, and inference/stub.py returning a deterministic p\_fake (for example a scripted ramp, or high when the window RMS pattern matches a test flag) so the UI and integration tests can run without a model. Select the engine via MODEL\_BACKEND env var (stub or hf).

### Step 4: API layer (1-1.5 h)

**Prompt:**

> Implement POST /api/v1/predict (multipart file, 10 MB cap, returns verdict, mean p\_fake, per-window scores, duration; clear 4xx errors for empty or unsupported files) and WS /ws/mic that accepts PCM16 frames, runs Windower -> engine -> smoothing -> state machine, and sends the JSON messages from section 2.2. Clean up on disconnect. Add integration tests using the stub engine, including irregular chunk sizes and mid-stream disconnect.

### Step 5: Dashboard (2-3 h, can run in parallel)

**Prompt:**

> Build the React dashboard against the schema in section 2.2: a large confidence meter coloured by state, a rolling Recharts line of p\_smooth, an alert banner (with optional beep), a Start/Stop mic button using an AudioWorklet that downsamples to 16 kHz PCM16 and sends it over WebSocket, a file upload card showing the verdict, and two demo buttons that upload bundled real/fake clips. Put the socket logic in hooks/useVoxSocket.ts with a reducer, auto-reconnect, and Vitest tests for the reducer.

### Step 6: Real model (1-3 h)

**Prompt:**

> Implement inference/hf\_engine.py using a pretrained audio-classification deepfake/anti-spoofing checkpoint from Hugging Face (I will tell you which; if none chosen, search the Hub for one with a permissive licence and a small footprint). Map its labels to p\_fake explicitly, warm up at startup, run on CPU, and log per-window latency. Add a benchmark script in backend/scripts/bench.py and a test that checks p\_fake is in \[0,1\] and the output shape is stable.

**Choosing a model (do this yourself or with me):** check licence, size, expected sample rate, label mapping, and test it on 5 real and 5 cloned clips before committing to it.

### Step 7: Demo data and evaluation (1-2 h)

- Record 10+ real clips (different people, rooms, mics).
- Generate 10+ fake clips with XTTS and/or ElevenLabs, ideally cloning a teammate from 30 s of audio.
- Put 3 of each in `demo/` for the one-click buttons; keep the rest for evaluation.

**Prompt:**

> Write backend/scripts/evaluate.py that runs every clip in demo/real and demo/fake through the engine and prints accuracy, mean score per class, and the false-alarm rate at the ALERT threshold. Save results to docs/EVAL.md.

### Step 8: Polish and freeze (1 h)

README with run instructions, `.env.example`, final lint and tests, screen recording of the demo.

---

## 4. Testing for the prototype

| Layer | What | Tool |
| --- | --- | --- |
| Unit | windowing counts, buffer cap, PCM decode, smoothing, state machine | pytest, hypothesis |
| Integration | `/predict` errors and success; `/ws/mic` with chunked PCM; disconnect cleanup | pytest-asyncio, httpx, Starlette TestClient |
| Frontend | reducer and hook logic, meter state colours | Vitest, Testing Library |
| Manual | mic demo with a real voice and with a cloned voice played from a speaker | checklist below |
| Perf | per-window inference latency, 5 min soak | `scripts/bench.py` |

**Manual demo checklist**

- [ ] Real voice into mic for 30 s: state stays NORMAL.
- [ ] Cloned clip played near the mic: ALERT within about 5 s.
- [ ] Upload real and fake clips: correct verdicts.
- [ ] Close the tab mid-stream: server logs a clean disconnect.
- [ ] Run all of the above 3 times in a row.

Known prototype caveat: playing a clone through speakers adds room acoustics and mic compression, which can change scores. Test that exact setup, and also test by uploading the raw files.

---

## 5. CI for the prototype

One workflow, `ci.yml`, on pull requests and pushes to `main`:

- Backend job: Python 3.11, install, `ruff check`, `ruff format --check`, `mypy app`, `pytest`.
- Frontend job: Node 20, `npm ci`, lint, typecheck, `vitest --run`, `npm run build`.
- Cancel in-progress runs per branch.
- No model downloads in CI; tests use the stub engine.

Deployment, Docker image publishing, Playwright e2e and model gates come after the prototype, as in the full CI/CD section.

---

## 6. Risks and fallbacks

| Risk | Fallback |
| --- | --- |
| Pretrained model performs poorly on clones | Try a second checkpoint; as a last resort fine-tune a small head on your clips (training comes after the prototype) |
| Browser audio capture issues (sample rate, permissions) | Resample in the worklet, show a clear permission error, keep file upload as the guaranteed path |
| Latency too high | Smaller model, longer hop (1 s), int8 ONNX export |
| Agent drifts from the plan | Re-point it at AGENTS.md, one step per session, review diffs before commits |

## 7. Handoff between tools

When tokens run out, ask the agent to write `HANDOFF.md`: steps completed, current step, failing tests, how to run, decisions made. In the next tool: "Read AGENTS.md, docs/PROTOTYPE.md and HANDOFF.md, then continue from the current step."

## 8. After the prototype

Telephony augmentation and retrain, Twilio call path plus SMS, saliency view, deployment, Playwright e2e, pitch and backup video. These are in the full roadmap.
