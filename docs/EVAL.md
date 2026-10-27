# VoxGuard Evaluation & Benchmark Report

**Date:** 2026-10-27 16:51:11 UTC  
**Model Backend:** `stub` (`stub`)  
**Evaluation Corpus:** `demo/real/` and `demo/fake/`  

## 1. Summary Metrics

| Metric | Value | Target / SLA | Status |
| :--- | :--- | :--- | :--- |
| **Overall Accuracy** | **100.0%** | &ge; 90.0% | PASS |
| **Mean Real Score** | `0.120` | &le; 0.250 | PASS |
| **Mean Fake Score** | `0.880` | &ge; 0.750 | PASS |
| **False Alarm Rate (FAR)** | `0.0%` | &le; 5.0% | PASS |
| **Miss Rate (FRR)** | `0.0%` | &le; 5.0% | PASS |
| **Equal Error Rate (EER)** | `0.0%` | &le; 10.0% | PASS |

## 2. Per-Sample Telemetry Details

| Clip File | Class | Dur (s) | Windows | Mean $p_\text{fake}$ | Peak $p_\text{smooth}$ | Final State | Alert Emitted? | Verdict | Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `real_sample_1.wav` | REAL | 3.0 | 3 | `0.120` | `0.120` | `NORMAL` | NO | **REAL** | PASS |
| `real_sample_2.wav` | REAL | 3.5 | 4 | `0.120` | `0.120` | `NORMAL` | NO | **REAL** | PASS |
| `real_sample_3.wav` | REAL | 4.0 | 5 | `0.120` | `0.120` | `NORMAL` | NO | **REAL** | PASS |
| `fake_sample_1.wav` | FAKE | 3.0 | 3 | `0.880` | `0.880` | `ALERT` | YES | **FAKE** | PASS |
| `fake_sample_2.wav` | FAKE | 3.5 | 4 | `0.880` | `0.880` | `ALERT` | YES | **FAKE** | PASS |
| `fake_sample_3.wav` | FAKE | 4.0 | 5 | `0.880` | `0.880` | `ALERT` | YES | **FAKE** | PASS |

## 3. Evaluation Methodology
- **Pipeline**: 16 kHz Mono Float32 &rarr; 2.0 s Windows (0.5 s Hop) &rarr; Model &rarr; Smoothing ($N=6$) &rarr; Hysteresis State Machine.
- **Evaluation Standard**: Zero raw streaming audio persisted to disk (in-memory analysis).
- **Report Generation**: Automatically generated via `python backend/scripts/evaluate.py`.
