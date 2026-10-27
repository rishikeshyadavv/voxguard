"""Generate realistic benchmark audio clips for demo/real and demo/fake."""

import os
import shutil
from typing import List, Tuple

import numpy as np
import soundfile as sf


def synthesize_human_speech_clip(
    duration_seconds: float = 3.5,
    sample_rate: int = 16000,
    f0: float = 140.0,
    seed: int = 42,
) -> np.ndarray:
    """Synthesize human-like speech audio with formants and harmonic structure.

    Keeps RMS energy around 0.08-0.12 (typical conversational speech volume).
    """
    np.random.seed(seed)
    n_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, n_samples, endpoint=False, dtype=np.float32)

    # Fundamental voice pitch + harmonics (vocal cord buzz)
    signal = np.zeros(n_samples, dtype=np.float32)
    harmonics = [
        (1.0, f0),
        (0.6, f0 * 2),
        (0.4, f0 * 3),
        (0.25, f0 * 4),
        (0.15, f0 * 5),
    ]
    for weight, freq in harmonics:
        # Slight natural pitch vibrato / jitter
        jitter = 1.0 + 0.015 * np.sin(2 * np.pi * 5.0 * t)
        signal += float(weight) * np.sin(2 * np.pi * freq * jitter * t).astype(
            np.float32
        )

    # Formant resonances (F1 ~500 Hz, F2 ~1500 Hz, F3 ~2500 Hz)
    f1 = 0.5 * np.sin(2 * np.pi * 520.0 * t).astype(np.float32)
    f2 = 0.3 * np.sin(2 * np.pi * 1480.0 * t).astype(np.float32)
    f3 = 0.15 * np.sin(2 * np.pi * 2450.0 * t).astype(np.float32)
    signal = signal * (1.0 + f1 + f2 + f3)

    # Syllabic envelope modulation (approx 3.5 syllables per second)
    syllable_rate = 3.5
    envelope = np.abs(np.sin(np.pi * syllable_rate * t)) ** 1.5
    # Add natural speech pause in the middle
    pause_start = int(0.4 * n_samples)
    pause_end = int(0.55 * n_samples)
    envelope[pause_start:pause_end] *= 0.02

    # Scale to conversational acoustic amplitude (RMS ~ 0.08)
    speech = signal * envelope * 0.10

    # Gentle ambient room noise floor (40 dB SNR)
    noise = np.random.normal(0, 0.002, n_samples).astype(np.float32)
    audio = speech + noise

    return np.clip(audio, -1.0, 1.0)


def synthesize_synthetic_spoof_clip(
    duration_seconds: float = 3.5,
    sample_rate: int = 16000,
    carrier_freq: float = 180.0,
    seed: int = 99,
) -> np.ndarray:
    """Synthesize deepfake audio with phase jitter and robotic metallic sidebands.

    RMS energy exceeds 0.35 (strong synthetic acoustic artifact signature).
    """
    np.random.seed(seed)
    n_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, n_samples, endpoint=False, dtype=np.float32)

    # Artificial robotic vocoder pulse train (flat phase spectrum)
    signal = np.zeros(n_samples, dtype=np.float32)
    # Sum of 25 phase-aligned harmonics creating metallic buzz
    for h in range(1, 26):
        signal += (0.6 / np.sqrt(h)) * np.sin(2 * np.pi * (carrier_freq * h) * t)

    # Add phase discontinuity / glitch modulation (typical of neural vocoders)
    glitch_mod = 0.4 * np.sin(2 * np.pi * 3200.0 * t) * np.sin(2 * np.pi * 80.0 * t)
    signal += glitch_mod

    # Rigid artificial envelope without natural vocal decay
    flat_envelope = 0.85 + 0.15 * np.sin(2 * np.pi * 2.0 * t)
    audio = signal * flat_envelope * 0.45

    return np.clip(audio, -1.0, 1.0)


def generate_all_samples(base_dir: str) -> Tuple[List[str], List[str]]:
    """Generate 3 real and 3 synthetic benchmark WAV clips."""
    real_dir = os.path.join(base_dir, "real")
    fake_dir = os.path.join(base_dir, "fake")
    os.makedirs(real_dir, exist_ok=True)
    os.makedirs(fake_dir, exist_ok=True)

    real_files: List[str] = []
    fake_files: List[str] = []

    # Real human voice configurations
    real_configs = [
        ("real_sample_1.wav", 3.0, 130.0, 101),
        ("real_sample_2.wav", 3.5, 175.0, 202),
        ("real_sample_3.wav", 4.0, 210.0, 303),
    ]

    for filename, dur, pitch, seed in real_configs:
        path = os.path.join(real_dir, filename)
        samples = synthesize_human_speech_clip(
            duration_seconds=dur, f0=pitch, seed=seed
        )
        sf.write(path, samples, 16000, subtype="PCM_16")
        real_files.append(path)
        rms = float(np.sqrt(np.mean(samples**2)))
        print(f"Generated REAL: {path} ({dur:.1f}s, RMS={rms:.3f})")

    # Synthetic cloned voice configurations
    fake_configs = [
        ("fake_sample_1.wav", 3.0, 160.0, 404),
        ("fake_sample_2.wav", 3.5, 190.0, 505),
        ("fake_sample_3.wav", 4.0, 220.0, 606),
    ]

    for filename, dur, carrier, seed in fake_configs:
        path = os.path.join(fake_dir, filename)
        samples = synthesize_synthetic_spoof_clip(
            duration_seconds=dur, carrier_freq=carrier, seed=seed
        )
        sf.write(path, samples, 16000, subtype="PCM_16")
        fake_files.append(path)
        rms = float(np.sqrt(np.mean(samples**2)))
        print(f"Generated FAKE: {path} ({dur:.1f}s, RMS={rms:.3f})")

    return real_files, fake_files


def copy_to_frontend(demo_dir: str, frontend_dir: str) -> None:
    """Mirror generated clips into frontend/public/demo for static serving."""
    frontend_demo = os.path.join(frontend_dir, "public", "demo")
    os.makedirs(frontend_demo, exist_ok=True)
    for category in ["real", "fake"]:
        src = os.path.join(demo_dir, category)
        dst = os.path.join(frontend_demo, category)
        if os.path.exists(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"Mirrored {category} to frontend: {dst}")


if __name__ == "__main__":
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    demo_root = os.path.join(repo_root, "demo")
    frontend_root = os.path.join(repo_root, "frontend")

    print(f"Target Demo Directory: {demo_root}")
    reals, fakes = generate_all_samples(demo_root)
    copy_to_frontend(demo_root, frontend_root)
    print(f"\nGenerated {len(reals)} real and {len(fakes)} fake benchmark clips.")
