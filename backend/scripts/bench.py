"""Benchmark inference engine latency on 2.0 s audio windows on CPU."""

import argparse
import os
import sys
import time
from typing import List

import numpy as np

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.inference.factory import get_inference_engine


def generate_benchmark_windows(
    num_windows: int = 10, sample_rate: int = 16000
) -> List[np.ndarray]:
    """Synthesize 2.0 s test windows: silence, sine tones, and noise."""
    samples_per_window = 2 * sample_rate
    windows = []

    # 1. Silence
    windows.append(np.zeros(samples_per_window, dtype=np.float32))

    # 2. Sine waves (different frequencies)
    t = np.linspace(0, 2.0, samples_per_window, endpoint=False, dtype=np.float32)
    for freq in [220.0, 440.0, 880.0, 1500.0]:
        sine = 0.5 * np.sin(2 * np.pi * freq * t)
        windows.append(sine)

    # 3. Gaussian noise (different amplitudes)
    np.random.seed(42)
    for amp in [0.05, 0.2, 0.5, 0.8]:
        noise = (amp * np.random.randn(samples_per_window)).astype(np.float32)
        windows.append(np.clip(noise, -1.0, 1.0))

    # Remaining if any
    while len(windows) < num_windows:
        windows.append(
            np.random.uniform(-0.3, 0.3, samples_per_window).astype(np.float32)
        )

    return windows[:num_windows]


def run_benchmark(
    backend: str = "stub",
    iterations_per_window: int = 10,
    max_latency_ms: float = 750.0,
) -> int:
    """Run benchmark loop and assert CPU latency threshold."""
    print("=== VOXGUARD INFERENCE BENCHMARK ===")
    print(f"Backend: {backend}")
    print(f"Max Allowable Mean Latency: {max_latency_ms:.1f} ms")

    engine = get_inference_engine(backend)
    print(f"Loaded Engine: {engine.model_name} (v{engine.version})")

    # Warmup
    print("Warming up inference engine...")
    engine.warmup()

    test_windows = generate_benchmark_windows(num_windows=10)
    latencies_ms: List[float] = []

    print(
        f"Benchmarking {len(test_windows)} windows x {iterations_per_window} iters..."
    )
    for w_idx, window in enumerate(test_windows):
        for _ in range(iterations_per_window):
            start = time.perf_counter()
            _ = engine.predict(window)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies_ms.append(elapsed_ms)

    mean_lat = float(np.mean(latencies_ms))
    median_lat = float(np.median(latencies_ms))
    p95_lat = float(np.percentile(latencies_ms, 95))
    min_lat = float(np.min(latencies_ms))
    max_lat = float(np.max(latencies_ms))

    print("\n--- RESULTS ---")
    print(f"Total Inferences : {len(latencies_ms)}")
    print(f"Mean Latency     : {mean_lat:.2f} ms")
    print(f"Median Latency   : {median_lat:.2f} ms")
    print(f"p95 Latency      : {p95_lat:.2f} ms")
    print(f"Min / Max        : {min_lat:.2f} ms / {max_lat:.2f} ms")

    if mean_lat > max_latency_ms:
        print(
            f"\n[FAIL] Mean latency {mean_lat:.2f} ms exceeded {max_latency_ms:.1f} ms!"
        )
        return 1

    print(f"\n[PASS] Latency benchmark satisfied under {max_latency_ms:.1f} ms SLA.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VoxGuard Inference Latency Benchmark")
    parser.add_argument(
        "--backend",
        default=os.getenv("MODEL_BACKEND", "stub"),
        help="Engine backend ('stub', 'hf')",
    )
    parser.add_argument(
        "--threshold", type=float, default=750.0, help="Max mean latency in ms"
    )
    args = parser.parse_args()

    sys.exit(run_benchmark(backend=args.backend, max_latency_ms=args.threshold))
