"""Automated evaluation and benchmark reporting for VoxGuard anti-spoofing."""

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

import numpy as np

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.audio.io import load_audio_file
from app.audio.windowing import Windower
from app.decision.smoothing import ScoreSmoother
from app.decision.state_machine import StateMachine
from app.inference.factory import get_inference_engine


def evaluate_clip(
    file_path: str,
    true_label: int,  # 0 for real, 1 for fake
    engine: Any,
) -> Dict[str, Any]:
    """Run a single audio file through the full VoxGuard analysis pipeline."""
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    audio = load_audio_file(file_bytes, target_sr=16000)
    duration_sec = len(audio) / 16000.0

    windower = Windower(
        window_duration_seconds=2.0,
        hop_duration_seconds=0.5,
        sample_rate=16000,
    )
    windows = windower.add_chunk(audio)

    smoother = ScoreSmoother(window_size=6)
    sm = StateMachine()

    raw_scores: List[float] = []
    smooth_scores: List[float] = []
    alert_triggered = False

    for window in windows:
        p_fake = float(engine.predict(window))
        raw_scores.append(p_fake)
        p_smooth = smoother.append(p_fake)
        smooth_scores.append(p_smooth)
        update = sm.update(p_smooth)
        if update.alert_triggered or update.state.value == "ALERT":
            alert_triggered = True

    mean_p_fake = float(np.mean(raw_scores)) if raw_scores else 0.0
    peak_p_smooth = float(np.max(smooth_scores)) if smooth_scores else 0.0
    verdict = "FAKE" if mean_p_fake >= 0.5 else "REAL"
    predicted_label = 1 if verdict == "FAKE" else 0
    is_correct = predicted_label == true_label

    return {
        "file": os.path.basename(file_path),
        "true_label": "REAL" if true_label == 0 else "FAKE",
        "duration_sec": round(duration_sec, 2),
        "windows": len(windows),
        "mean_p_fake": round(mean_p_fake, 3),
        "peak_p_smooth": round(peak_p_smooth, 3),
        "final_state": sm.state.value,
        "alert_triggered": alert_triggered,
        "verdict": verdict,
        "is_correct": is_correct,
    }


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate overall accuracy, FAR, FRR, and approximate EER."""
    total = len(results)
    if total == 0:
        return {}

    correct = sum(1 for r in results if r["is_correct"])
    accuracy = (correct / total) * 100.0

    reals = [r for r in results if r["true_label"] == "REAL"]
    fakes = [r for r in results if r["true_label"] == "FAKE"]

    mean_real_score = (
        float(np.mean([r["mean_p_fake"] for r in reals])) if reals else 0.0
    )
    mean_fake_score = (
        float(np.mean([r["mean_p_fake"] for r in fakes])) if fakes else 0.0
    )

    # False Alarm Rate (FAR): real clips triggering ALERT or p_smooth >= 0.75
    false_alarms = sum(1 for r in reals if r["alert_triggered"])
    far = (false_alarms / len(reals) * 100.0) if reals else 0.0

    # False Rejection Rate (FRR) / Miss Rate: fake clips classified as REAL (< 0.5)
    misses = sum(1 for r in fakes if not r["is_correct"])
    frr = (misses / len(fakes) * 100.0) if fakes else 0.0

    # Approximate Equal Error Rate (EER) across threshold sweep [0.0, 1.0]
    eer = 0.0
    min_diff = float("inf")
    for thresh in np.linspace(0.01, 0.99, 99):
        far_t = sum(1 for r in reals if r["mean_p_fake"] >= thresh) / max(1, len(reals))
        frr_t = sum(1 for r in fakes if r["mean_p_fake"] < thresh) / max(1, len(fakes))
        diff = abs(far_t - frr_t)
        if diff < min_diff:
            min_diff = diff
            eer = ((far_t + frr_t) / 2.0) * 100.0

    return {
        "accuracy": accuracy,
        "mean_real_score": mean_real_score,
        "mean_fake_score": mean_fake_score,
        "far": far,
        "frr": frr,
        "eer": eer,
    }


def write_eval_markdown(
    results: List[Dict[str, Any]],
    metrics: Dict[str, float],
    backend: str,
    model_name: str,
    output_path: str,
) -> None:
    """Generate docs/EVAL.md markdown report."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    acc_stat = "PASS" if metrics["accuracy"] >= 90.0 else "WARN"
    real_stat = "PASS" if metrics["mean_real_score"] <= 0.250 else "WARN"
    fake_stat = "PASS" if metrics["mean_fake_score"] >= 0.750 else "WARN"
    far_stat = "PASS" if metrics["far"] <= 5.0 else "WARN"
    frr_stat = "PASS" if metrics["frr"] <= 5.0 else "WARN"
    eer_stat = "PASS" if metrics["eer"] <= 10.0 else "WARN"

    md_lines = [
        "# VoxGuard Evaluation & Benchmark Report",
        "",
        f"**Date:** {timestamp}  ",
        f"**Model Backend:** `{backend}` (`{model_name}`)  ",
        "**Evaluation Corpus:** `demo/real/` and `demo/fake/`  ",
        "",
        "## 1. Summary Metrics",
        "",
        "| Metric | Value | Target / SLA | Status |",
        "| :--- | :--- | :--- | :--- |",
        (
            f"| **Overall Accuracy** | **{metrics['accuracy']:.1f}%** | "
            f"&ge; 90.0% | {acc_stat} |"
        ),
        (
            f"| **Mean Real Score** | `{metrics['mean_real_score']:.3f}` | "
            f"&le; 0.250 | {real_stat} |"
        ),
        (
            f"| **Mean Fake Score** | `{metrics['mean_fake_score']:.3f}` | "
            f"&ge; 0.750 | {fake_stat} |"
        ),
        (
            f"| **False Alarm Rate (FAR)** | `{metrics['far']:.1f}%` | "
            f"&le; 5.0% | {far_stat} |"
        ),
        f"| **Miss Rate (FRR)** | `{metrics['frr']:.1f}%` | &le; 5.0% | {frr_stat} |",
        (
            f"| **Equal Error Rate (EER)** | `{metrics['eer']:.1f}%` | "
            f"&le; 10.0% | {eer_stat} |"
        ),
        "",
        "## 2. Per-Sample Telemetry Details",
        "",
        (
            "| Clip File | Class | Dur (s) | Windows | Mean $p_\\text{fake}$ | "
            "Peak $p_\\text{smooth}$ | Final State | Alert Emitted? | "
            "Verdict | Result |"
        ),
        ("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"),
    ]

    for r in results:
        status_icon = "PASS" if r["is_correct"] else "FAIL"
        alert_str = "YES" if r["alert_triggered"] else "NO"
        line = (
            f"| `{r['file']}` | {r['true_label']} | {r['duration_sec']} | "
            f"{r['windows']} | `{r['mean_p_fake']:.3f}` | "
            f"`{r['peak_p_smooth']:.3f}` | `{r['final_state']}` | "
            f"{alert_str} | **{r['verdict']}** | {status_icon} |"
        )
        md_lines.append(line)

    pipeline_doc = (
        "- **Pipeline**: 16 kHz Mono Float32 &rarr; 2.0 s Windows (0.5 s Hop) "
        "&rarr; Model &rarr; Smoothing ($N=6$) &rarr; Hysteresis State Machine."
    )
    privacy_doc = (
        "- **Evaluation Standard**: Zero raw streaming audio persisted to disk "
        "(in-memory analysis)."
    )
    report_doc = (
        "- **Report Generation**: Automatically generated via "
        "`python backend/scripts/evaluate.py`."
    )

    md_lines.extend(
        [
            "",
            "## 3. Evaluation Methodology",
            pipeline_doc,
            privacy_doc,
            report_doc,
            "",
        ]
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"\nSaved evaluation report to: {output_path}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="VoxGuard Evaluation & Benchmark Suite"
    )
    parser.add_argument(
        "--backend",
        default="stub",
        choices=["stub", "hf"],
        help="Inference engine backend",
    )
    parser.add_argument(
        "--data-dir", default="demo", help="Base directory containing real/ and fake/"
    )
    parser.add_argument(
        "--out", default="docs/EVAL.md", help="Output path for evaluation markdown"
    )
    args = parser.parse_args()

    # Resolve repo root and paths
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if os.path.isabs(args.data_dir):
        data_dir = args.data_dir
    elif os.path.isdir(os.path.join(os.getcwd(), args.data_dir)):
        data_dir = os.path.abspath(os.path.join(os.getcwd(), args.data_dir))
    else:
        data_dir = os.path.join(repo_root, args.data_dir)

    if os.path.isabs(args.out):
        out_path = args.out
    else:
        out_path = os.path.join(repo_root, args.out)

    real_dir = os.path.join(data_dir, "real")
    fake_dir = os.path.join(data_dir, "fake")

    if not os.path.isdir(real_dir) or not os.path.isdir(fake_dir):
        print(f"[ERR]: Demo directories not found at {data_dir}")
        return 1

    engine = get_inference_engine(args.backend)
    engine.warmup()

    results: List[Dict[str, Any]] = []

    print(f"\n--- EVALUATING REAL CLIPS ({real_dir}) ---")
    for f in sorted(os.listdir(real_dir)):
        if f.endswith((".wav", ".mp3", ".flac", ".ogg")):
            p = os.path.join(real_dir, f)
            res = evaluate_clip(p, true_label=0, engine=engine)
            results.append(res)
            print(
                f"  REAL: {f:<20} | mean p_fake: {res['mean_p_fake']:.3f} | "
                f"verdict: {res['verdict']} [{res['is_correct']}]"
            )

    print(f"\n--- EVALUATING FAKE CLIPS ({fake_dir}) ---")
    for f in sorted(os.listdir(fake_dir)):
        if f.endswith((".wav", ".mp3", ".flac", ".ogg")):
            p = os.path.join(fake_dir, f)
            res = evaluate_clip(p, true_label=1, engine=engine)
            results.append(res)
            print(
                f"  FAKE: {f:<20} | mean p_fake: {res['mean_p_fake']:.3f} | "
                f"verdict: {res['verdict']} [{res['is_correct']}]"
            )

    metrics = compute_metrics(results)

    print("\n--- SUMMARY METRICS ---")
    print(f"Total Clips Evaluated : {len(results)}")
    print(f"Accuracy              : {metrics['accuracy']:.1f}%")
    print(f"Mean Real Score       : {metrics['mean_real_score']:.3f}")
    print(f"Mean Fake Score       : {metrics['mean_fake_score']:.3f}")
    print(f"False Alarm Rate (FAR): {metrics['far']:.1f}%")
    print(f"Miss Rate (FRR)       : {metrics['frr']:.1f}%")
    print(f"Equal Error Rate (EER): {metrics['eer']:.1f}%")

    write_eval_markdown(
        results,
        metrics,
        backend=args.backend,
        model_name=engine.model_name,
        output_path=out_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
