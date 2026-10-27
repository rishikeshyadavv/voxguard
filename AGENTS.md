# AGENTS.md — VoxGuard Hackathon Directives

## 1. Operating Rules for AI Agents
- **Source of Truth**: Read `docs/PROTOTYPE.md` and `docs/` before generating code. Do not deviate from interface contracts, state machine logic, or API definitions without explicit user instruction.
- **Scope Discipline**: Respect non-goals. Build strictly what is outlined in the active step. Do NOT unilaterally add user authentication, external databases, cloud telemetry, or unrelated features.
- **Test-Driven Delivery**: Write unit tests alongside all logic. Every agent session MUST end with all tests passing (`make test`). Never commit code with failing tests.
- **Privacy Enforcement**: Audio streams MUST be processed strictly in memory (ring buffer). Never write raw streaming call audio to persistent disk.

## 2. Technical Standards
- **Python**: 3.11 strictly. (Python 3.13 deprecates/removes `audioop` and breaks legacy audio tooling).
- **Backend Quality**: 100% type hints (`mypy app`), lint-clean (`ruff check .`), formatted (`ruff format --check .`).
- **Audio Pipeline**:
  - Sample rate: 16 kHz mono float32.
  - Window: 2.0 s.
  - Hop: 0.5 s.
  - Ingest: Little-endian PCM16 chunks via WebSocket or standard uploads.
- **Inference Isolation**: All models must sit behind the `InferenceEngine` interface protocol. No API route may talk directly to Hugging Face or ONNX classes without going through the engine abstraction.
- **Frontend Quality**: TypeScript Strict (`npm run typecheck`), React 18/19 with Vite, Tailwind CSS, Recharts for rolling telemetry.

## 3. Session Cadence & Token Management
- Execute **one step at a time** as defined in `docs/PROTOTYPE.md`.
- Before closing or when token capacity is running out:
  1. Commit all working code (`git commit -m "feat/fix: ..."`).
  2. Generate or update `HANDOFF.md` containing:
     - Completed tasks and green tests.
     - Active failing tests or unfinished files.
     - Commands to run and verify current work.
     - Exact prompt instructions for the next agent session.