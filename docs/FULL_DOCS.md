# VoxGuard: Real-Time Deepfake Voice Detection for Live Calls

Project docs for SW-40 (Bits2Wave). Built for a 24-36 hour hackathon, written so an AI coding agent (agy CLI / opencode) can implement from it directly.

**How to use with agy CLI:** copy each section into `docs/` in your repo as `PRD.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CICD.md`, `TESTING.md`. Add a root `AGENTS.md` telling the agent to read `docs/` first and follow the conventions below. Work one roadmap phase per session, and commit after every green test run.

---

## 1. Product Requirements Document (PRD)

### 1.1 Problem

Voice-cloning scams (fake relatives, fake bank officials, CEO fraud) are rising, and victims have no way to know a live caller's voice is synthetic. Existing detectors work on uploaded files, not live calls.

### 1.2 Vision

A system that listens to a live call, scores the caller's voice in near real time, and warns the user (and a trusted contact) within seconds when the voice looks AI-generated.

### 1.3 Target users

- **Primary:** people at risk of voice scams (elderly users, families).
- **Secondary:** call centers and banks verifying callers.
- **Demo persona:** a parent receiving a call that sounds like their child.

### 1.4 Goals and non-goals

**Goals**

- G1: Detect synthetic speech on live phone-quality audio (8 kHz, compressed).
- G2: Alert within 3 seconds of speech start for clear fakes.
- G3: Show a live dashboard with confidence meter, spectrogram and alerts.
- G4: Notify a trusted contact by SMS on detection.
- G5: Report honest, cross-dataset accuracy numbers.

**Non-goals (do not build)**

- Video deepfakes, multi-language tuning, user accounts and billing, native mobile app, call recording storage.

### 1.5 User stories

| ID | Story | Priority |
| --- | --- | --- |
| U1 | As a user, I join a call and see a live real/fake confidence score | P0 |
| U2 | As a user, I get a visible and audible alert when the voice is likely fake | P0 |
| U3 | As a user, I can upload an audio file and get a verdict | P0 |
| U4 | As a user, I see which time/frequency regions drove the verdict | P1 |
| U5 | As a user, a trusted contact gets an SMS when an alert fires | P1 |
| U6 | As a judge, I can run a one-click demo with sample real and fake clips | P0 |
| U7 | As a user, I see a call history with verdict timeline | P2 |

### 1.6 Functional requirements

- FR1: Ingest audio via (a) Twilio Media Stream WebSocket, (b) browser microphone WebSocket, (c) file upload REST.
- FR2: Normalize audio to 16 kHz mono float32, then run windowed inference (2 s window, 0.5 s hop).
- FR3: Return per-window `fake_probability` in \[0,1\] and a smoothed score (mean of the last N windows, N configurable, default 6).
- FR4: Alert state machine: `NORMAL` -> `SUSPICIOUS` (smoothed > 0.5) -> `ALERT` (smoothed > 0.75 for 3 consecutive windows). Hysteresis to clear.
- FR5: Push live results to the dashboard over WebSocket.
- FR6: Generate a spectrogram saliency map for the latest window (Grad-CAM or occlusion).
- FR7: Send SMS via Twilio to the configured trusted number on `ALERT` (rate-limited, once per call).
- FR8: `/health`, `/metrics`, `/api/v1/predict` (file) endpoints.
- FR9: Demo mode that replays bundled clips through the same pipeline.

### 1.7 Non-functional requirements

| Area | Target |
| --- | --- |
| Latency | Inference under 500 ms per window on CPU; end-to-end under 1.5 s |
| Accuracy | EER under 10% on held-out dataset; under 20% on phone-degraded audio |
| Robustness | Works on 8 kHz G.711/AMR-degraded audio and moderate noise |
| Privacy | Audio processed in memory, never written to disk in live mode |
| Availability | Single instance is fine; must survive WebSocket reconnects |
| Portability | `docker compose up` runs everything locally |

### 1.8 Success metrics

- EER and AUC on in-domain and cross-domain test sets.
- False-alarm rate on real speech under 5% of calls.
- Demo: cloned voice triggers ALERT in under 5 s, real voice stays NORMAL, three times in a row.

### 1.9 Risks

| Risk | Mitigation |
| --- | --- |
| Model overfits to dataset artifacts | Cross-dataset eval, telephony augmentation, In-the-Wild data |
| Live demo failure | Replay mode, recorded backup video, pre-tested clips |
| Inference too slow on CPU | ONNX export, int8 quantization, smaller backbone |
| Twilio setup eats time | Browser-mic path built first; Twilio is a P1 add-on |
| False alarm on a real voice | Smoothing, hysteresis, tuned thresholds |

---

## 2. System Architecture

### 2.1 Overview

```
 Phone call / Browser mic / File upload
            |
   [Twilio Media Stream] (mulaw 8k, base64 JSON)
            |  WebSocket
            v
+---------------------------- FastAPI backend ----------------------------+
|  Ingest layer  ->  Audio pipeline  ->  Inference engine  ->  Decision    |
|  (ws/rest)        (decode, resample,   (ONNX Runtime)       (smoothing,   |
|                    ring buffer,                              state machine)|
|                    windowing)                                     |       |
|                                          Explainer (saliency) <---+       |
|                                                |                          |
|                         Broadcast hub (WebSocket) ----> Dashboard         |
|                         Notifier (Twilio SMS)                              |
+---------------------------------------------------------------------------+
            |
   SQLite (call sessions, verdicts)   Prometheus /metrics
```

### 2.2 Components

| Component | Responsibility | Tech |
| --- | --- | --- |
| Ingest | Accept Twilio, browser and file audio | FastAPI WebSocket + REST |
| Audio pipeline | mulaw decode, resample to 16 kHz, ring buffer, 2 s / 0.5 s windows, normalization | NumPy, SciPy, soxr (no `audioop`; Python 3.13 removed it, so pin 3.11) |
| Inference engine | Run model on a window, return fake probability | ONNX Runtime (CPU), int8 quantized |
| Decision engine | Moving average, thresholds, state machine with hysteresis | Pure Python, fully unit-testable |
| Explainer | Saliency over log-mel spectrogram | PyTorch Grad-CAM offline, or occlusion on ONNX |
| Broadcast hub | Fan-out of results to dashboard clients per session | asyncio + WebSocket |
| Notifier | SMS on ALERT, once per call | Twilio REST |
| Storage | Session and verdict metadata only, no audio | SQLite via SQLModel |
| Dashboard | Meter, rolling chart, spectrogram, alerts, demo controls | React + Vite + TypeScript + Tailwind + Recharts |
| Training | Fine-tune, augment, evaluate, export ONNX | PyTorch, torchaudio, HF Transformers; runs on Colab/Kaggle |

### 2.3 Model design

- **Backbone options (pick by time):**
  - A: `AASIST` or `RawNet2` (small, fast, good ASVspoof baselines).
  - B: `wav2vec2-base` or XLS-R fine-tune with a small classification head (stronger, heavier). Prefer a pretrained anti-spoofing checkpoint from Hugging Face if one is available, and fine-tune it rather than starting cold.
- **Training data:** ASVspoof 2019 LA, ASVspoof 2021 (DF/LA), WaveFake, In-the-Wild; plus your own clones made with XTTS and ElevenLabs.
- **Telephony augmentation (key differentiator):** downsample to 8 kHz and back, G.711 mulaw, AMR-NB codec via ffmpeg, additive noise (MUSAN), random gain, band-limit 300-3400 Hz, packet-loss gaps.
- **Evaluation:** train on set A, test on set B (cross-dataset); report EER, AUC, and false-alarm rate on real calls.
- **Export:** `torch.onnx.export` -> `onnxruntime.quantization.quantize_dynamic` -> verify output parity within 1e-3 against PyTorch.

### 2.4 Data flow (live call)

1. Twilio sends `start`, then `media` events (20 ms mulaw frames, base64), then `stop`.
2. Ingest decodes mulaw to PCM16, resamples 8k -> 16k, appends to the session ring buffer.
3. Every 0.5 s with at least 2 s buffered, the pipeline cuts a window, normalizes it and calls the inference engine.
4. Decision engine updates the smoothed score and state, and emits `{t, p_fake, p_smooth, state}`.
5. Hub pushes the message to the dashboard; on first `ALERT` the notifier sends SMS.
6. Saliency is computed on demand or every N windows, not on every window, to protect latency.

### 2.5 API contract

**REST**

- `GET /health` -> `{status, model_version}`
- `POST /api/v1/predict` (multipart `file`) -> `{verdict, p_fake, windows:[{t,p}], duration}`
- `GET /api/v1/sessions` / `GET /api/v1/sessions/{id}`
- `POST /twilio/voice` -> TwiML returning `<Connect><Stream url="wss://.../ws/twilio"/></Connect>`

**WebSocket**

- `/ws/twilio` for Twilio Media Streams (JSON events)
- `/ws/mic?session=ID` for browser audio (binary PCM16 16 kHz chunks)
- `/ws/dashboard?session=ID` for server pushes:

```json
{"type":"score","t":12.5,"p_fake":0.83,"p_smooth":0.71,"state":"SUSPICIOUS"}
{"type":"alert","t":14.0,"p_smooth":0.82}
{"type":"saliency","t":14.0,"png_base64":"..."}
```

### 2.6 Repository layout

```
voxguard/
  AGENTS.md
  docs/                  PRD.md ARCHITECTURE.md ROADMAP.md CICD.md TESTING.md
  backend/
    app/
      main.py  config.py
      ingest/   (twilio.py, mic.py, upload.py)
      audio/    (codec.py, resample.py, buffer.py, windowing.py)
      inference/(engine.py, onnx_model.py)
      decision/ (smoothing.py, state_machine.py)
      explain/  (saliency.py)
      notify/   (sms.py)
      db/       (models.py)
    tests/      (unit/, integration/, fixtures/)
    pyproject.toml
  frontend/
    src/ (components/, hooks/, pages/, lib/)
    tests/ e2e/
  training/
    configs/ notebooks/ augment.py train.py evaluate.py export_onnx.py
  models/                (git-lfs or released artifact, not committed raw)
  demo/                  (real/ and fake/ sample clips, replay script)
  docker-compose.yml  Dockerfile.backend  Dockerfile.frontend
  .github/workflows/
```

### 2.7 Configuration (env vars)

`MODEL_PATH`, `WINDOW_SEC=2.0`, `HOP_SEC=0.5`, `SMOOTH_N=6`, `T_SUSPICIOUS=0.5`, `T_ALERT=0.75`, `ALERT_CONSECUTIVE=3`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`, `TRUSTED_CONTACT`, `PUBLIC_WS_URL`, `CORS_ORIGINS`. Secrets only via env or GitHub Secrets, never committed.

### 2.8 Deployment

- **Local/dev:** `docker compose up` (backend, frontend).
- **Demo hosting:** backend on Render, Fly.io or a Hugging Face Space (CPU is enough with ONNX int8); frontend on Vercel or Netlify; Twilio webhooks pointed at the public backend URL (ngrok as a fallback).
- **Training:** Colab or Kaggle GPU, artifacts pushed to Hugging Face Hub or GitHub Releases.

### 2.9 Security and privacy

No audio persisted in live mode; validate Twilio signatures on webhooks; cap upload size (10 MB) and duration; rate limit REST; strict CORS; SMS sent once per session; clear on-screen consent notice for the demo.

---

## 3. Development Roadmap

Assumes 4 people and about 36 hours. Scale phases proportionally if you have less. **P0 first, P1/P2 only if green.**

| Phase | Hours | Deliverable | Exit criteria |
| --- | --- | --- | --- |
| 0. Setup | 0-2 | Repo, folders, `AGENTS.md`, docs, CI skeleton, Docker compose, dataset downloads started | CI runs green on an empty test; everyone can run `docker compose up` |
| 1. Model baseline | 2-10 | Pretrained checkpoint evaluated; first fine-tune; ONNX export | EER number on ASVspoof eval; ONNX parity test passes |
| 2. Backend core (parallel with 1) | 2-12 | Audio pipeline, decision engine, `/predict`, `/ws/mic`, stub model | Unit tests green; file upload returns a verdict using the stub model |
| 3. Dashboard (parallel) | 4-14 | Live meter, chart, alert banner, demo controls, upload page | UI shows live scores from a mocked WebSocket |
| 4. Integration | 12-18 | Real ONNX model wired in; end-to-end browser-mic flow | Speak into mic: score updates under 1.5 s |
| 5. Telephony | 18-24 | Twilio Media Stream, SMS alert, public deploy | Real phone call produces live scores; SMS arrives |
| 6. Robustness | 20-28 | Telephony-augmented retrain, cross-dataset eval, threshold tuning | Phone-degraded EER reported; false-alarm check on 20+ real clips |
| 7. Explainability and polish | 26-32 | Saliency view, replay demo mode, UI polish, README | Judge can run demo mode in one click |
| 8. Demo prep | 32-36 | Pitch deck, rehearsals, backup video, final freeze | 3 clean consecutive demo runs; code freeze at H-3 |

### Milestone checkpoints

- **M1 (H10):** model + ONNX exists, even if mediocre.
- **M2 (H18):** mic-to-dashboard works end to end. **If this slips, drop Twilio and use the browser mic plus replay.**
- **M3 (H24):** deployed publicly.
- **M4 (H32):** feature freeze.

### Suggested agy CLI session order

1. "Read docs/ and scaffold the repo structure, pyproject, Dockerfile, compose, and CI workflow."
2. "Implement audio/ (mulaw decode, resample, ring buffer, windowing) with unit tests first."
3. "Implement decision/ state machine and smoothing with property-based tests."
4. "Implement inference engine behind an interface with a stub and an ONNX backend."
5. "Implement ingest endpoints and the dashboard WebSocket hub, with integration tests."
6. "Build the React dashboard against the documented WebSocket schema."
7. "Add Twilio ingest, TwiML endpoint, SMS notifier."
8. "Add saliency, replay mode, README."

When tokens run out: commit, write a `HANDOFF.md` (what is done, what is next, open bugs, how to run tests), then start the next tool with "read AGENTS.md, docs/, HANDOFF.md and continue."

### Suggested `AGENTS.md`

```
# Rules for AI agents
- Read docs/ before coding. Docs are the source of truth; propose doc changes, don't silently deviate.
- Python 3.11, type hints everywhere, ruff + mypy clean. Frontend: TypeScript strict.
- Write tests with the code. Run `make test` before every commit.
- Small commits, conventional commit messages.
- Never commit secrets, datasets or model binaries.
- Keep inference behind the InferenceEngine interface.
- No audio written to disk in live mode.
- Prefer simple solutions; hackathon scope. Check non-goals in PRD before adding features.
```

---

## 4. CI/CD Pipeline (GitHub Actions)

### 4.1 Principles

Fast feedback (under 5 minutes), everything runs on every pull request, `main` is always deployable, the model and datasets are never in CI, and deploys are automatic from `main`.

### 4.2 Branching

`main` (protected, deploys) <- short-lived `feat/*` branches via PR. Required checks: backend, frontend, docker build. For a hackathon, allow squash merges without mandatory human review but keep checks required.

### 4.3 Local gate (pre-commit)

ruff, ruff-format, mypy (backend), eslint and prettier (frontend), detect-secrets, check-added-large-files (limit 5 MB). A `Makefile` exposes `make lint`, `make test`, `make e2e`, `make up`.

### 4.4 CI workflow

`.github/workflows/ci.yml`

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: backend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11', cache: pip }
      - run: sudo apt-get update && sudo apt-get install -y ffmpeg libsndfile1
      - run: pip install -e '.[dev]'
      - run: ruff check . && ruff format --check .
      - run: mypy app
      - run: pytest tests/unit tests/integration --cov=app --cov-fail-under=70 -q

  frontend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
      - run: npm run lint && npm run typecheck
      - run: npm test -- --run
      - run: npm run build

  e2e:
    needs: [backend, frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose -f docker-compose.ci.yml up -d --build
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: cd frontend && npm ci && npx playwright install --with-deps chromium
      - run: cd frontend && npx playwright test
      - if: failure()
        uses: actions/upload-artifact@v4
        with: { name: playwright-report, path: frontend/playwright-report }

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gitleaks/gitleaks-action@v2
      - run: pip install pip-audit && pip-audit -r backend/requirements.lock || true
```

### 4.5 Docker build and push

`.github/workflows/docker.yml`: on push to `main`, build `Dockerfile.backend` and `Dockerfile.frontend` with `docker/build-push-action`, tag `ghcr.io/<org>/voxguard-backend:sha-<shortsha>` and `:latest`, use GitHub cache (`type=gha`). The backend image downloads the ONNX model at build time from a pinned Hugging Face or GitHub Release URL with a SHA-256 check.

### 4.6 Deploy (CD)

- **Frontend:** Vercel or Netlify Git integration, with a preview deploy per PR and production deploy on `main`.
- **Backend:** Render or Fly.io deploy hook triggered after the Docker job succeeds:

```yaml
  deploy:
    needs: [docker]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: curl -fsS -X POST "${{ secrets.RENDER_DEPLOY_HOOK }}"
      - name: Smoke test
        run: |
          for i in {1..20}; do
            curl -fsS "${{ secrets.BACKEND_URL }}/health" && exit 0
            sleep 10
          done
          exit 1
```

- **Rollback:** redeploy the previous `sha-` image tag; keep the last known-good tag noted in `HANDOFF.md`.

### 4.7 Model pipeline (separate, manual)

`model.yml` is `workflow_dispatch` only: runs the ONNX parity test and the evaluation on a small fixed sample set against a downloaded model, and fails if EER on the sample exceeds a threshold. This is the model quality gate. Training itself happens on Colab/Kaggle, not in CI.

### 4.8 Secrets

GitHub Secrets: `TWILIO_*`, `RENDER_DEPLOY_HOOK`, `BACKEND_URL`, `HF_TOKEN`. Never in code, `.env` is gitignored, `.env.example` is committed.

---

## 5. Testing Strategy

### 5.1 Philosophy

Test the parts that break demos: audio handling, the decision logic, the WebSocket flow and latency. Model quality is tested by evaluation metrics, not by unit asserts. Aim for confidence, not 100% coverage.

### 5.2 Test pyramid

| Layer | Scope | Tools | Run |
| --- | --- | --- | --- |
| Unit | codec, resample, buffer, windowing, smoothing, state machine, config | pytest, hypothesis | every commit |
| Component | inference engine with stub and ONNX, explainer shape checks | pytest | every commit |
| Integration | WebSocket ingest -> pipeline -> dashboard hub; REST `/predict`; Twilio payload replay | pytest-asyncio, httpx, Starlette TestClient | every PR |
| Frontend unit | components, hooks, WebSocket reducer | Vitest, Testing Library | every PR |
| E2E | Dashboard in a browser with replay mode against the real backend | Playwright | every PR |
| Model evaluation | EER, AUC, per-condition metrics | `training/evaluate.py` | manual and `model.yml` |
| Performance | latency, throughput, memory | pytest-benchmark, Locust or a custom async client | before demo |
| Demo rehearsal | full scripted run on demo hardware and network | checklist | final 6 hours |

### 5.3 Unit tests: key cases

- **Codec:** known mulaw sample decodes to expected PCM; round trip error below tolerance.
- **Resample:** 8k -> 16k length is exactly 2x, no clipping, sine frequency preserved.
- **Buffer and windowing:** window count for N seconds is correct; hop overlap is correct; partial frames carry over; buffer cap prevents unbounded growth.
- **Smoothing:** moving average with fewer than N samples; constant input converges.
- **State machine (use hypothesis):** never jumps NORMAL -> ALERT without passing the consecutive-window rule; hysteresis returns to NORMAL only below the lower threshold; ALERT SMS flag fires once per session.
- **Config:** invalid thresholds (suspicious >= alert) are rejected.

### 5.4 Integration tests

- Replay a recorded Twilio JSON event log (`tests/fixtures/twilio_session.jsonl`) into `/ws/twilio` with the stub model and assert the dashboard socket receives ordered score events and exactly one `alert`.
- Mic WebSocket with PCM chunks of odd sizes (irregular framing).
- Client disconnect mid-stream cleans up the session and does not leak tasks.
- `/predict` rejects oversized, wrong-format and silent files with clear errors.
- Twilio signature validation: valid accepted, invalid returns 403.
- SMS notifier mocked; assert one call per session and no call when the alert never fires.

### 5.5 Model evaluation protocol

1. **Splits:** train on ASVspoof 2019 LA train; validate on its dev; test on the eval set. **Cross-dataset:** test on In-the-Wild and your own cloned clips. Never tune thresholds on the test set.
2. **Metrics:** EER, AUC, and false-alarm rate at the chosen alert threshold.
3. **Condition breakdown:** clean 16 kHz, 8 kHz, mulaw, AMR-NB, with noise at 20/10/5 dB SNR, and by generator type if labelled.
4. **Real-voice false alarms:** at least 20 real clips from your team (different mics, accents, noisy rooms) must stay under the alert threshold.
5. **Release gate:** ONNX parity with PyTorch (max diff under 1e-3) and phone-degraded EER no worse than the agreed target; record results in `docs/EVAL.md`.
6. **Honesty rule:** the numbers in the pitch must come from this file.

### 5.6 Frontend tests

- Reducer handles `score`, `alert`, reconnect and out-of-order messages.
- Meter colors and alert banner follow state; accessible labels exist.
- E2E: open demo mode, play the real clip (state stays green), play the fake clip (alert banner within 5 s), upload a file (verdict shown), and a dropped WebSocket reconnects.

### 5.7 Performance and reliability targets

| Check | Target |
| --- | --- |
| ONNX inference per 2 s window (CPU) | under 500 ms p95 |
| End-to-end audio-in to dashboard | under 1.5 s p95 |
| Concurrent sessions on demo box | at least 5 without dropped windows |
| 30-minute soak | no memory growth beyond 10% |
| Backend cold start | under 60 s |

If inference misses the target: quantize, shorten the window, reduce hop frequency, or use a smaller backbone, in that order.

### 5.8 Demo rehearsal checklist

- [ ] 3 consecutive end-to-end runs pass: real stays NORMAL, clone triggers ALERT.
- [ ] Tested on the venue network or a phone hotspot, with a plan B for each.
- [ ] Backup: replay mode works offline; a recorded screen video is ready.
- [ ] Twilio number verified, SMS recipient number confirmed, trial limits checked.
- [ ] Demo clips pinned in `demo/`; model version frozen and noted.
- [ ] Laptop charged, audio output volume and mic input levels tested.
- [ ] Pitch rehearsed under 3 minutes; Q&A prepared (see below).

### 5.9 Likely judge questions to prepare for

- How does it work on compressed phone audio? (Telephony augmentation, results by condition.)
- What about generators the model hasn't seen? (Cross-dataset numbers, honest limitations, retraining path.)
- What is your false-alarm rate? (Measured on real clips, smoothing and hysteresis.)
- What about privacy? (In-memory only, no recordings.)
- How would this scale? (Stateless inference workers, per-session buffers, queue between ingest and inference.)

### 5.10 Definition of done (per feature)

Code merged via PR with green CI, tests written, docs updated if the contract changed, no new lint or type errors, and verified manually once in the running app.
