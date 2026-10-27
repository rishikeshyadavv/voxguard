"""Integration tests for POST /api/v1/predict."""

import io

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _generate_wav_bytes(
    duration_seconds: float = 3.0,
    sample_rate: int = 16000,
    amplitude: float = 0.5,
) -> bytes:
    """Helper to synthesize in-memory WAV audio bytes."""
    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
        dtype=np.float32,
    )
    # Sine tone
    audio = amplitude * np.sin(2 * np.pi * 440 * t)
    buffer = io.BytesIO()
    sf.write(buffer, audio, sample_rate, format="WAV")
    return buffer.getvalue()


def test_predict_valid_wav_low_energy() -> None:
    # Amplitude 0.1 -> RMS ~= 0.07 < 0.25 -> Stub returns p_fake=0.12 (REAL)
    wav_bytes = _generate_wav_bytes(duration_seconds=3.0, amplitude=0.1)

    response = client.post(
        "/api/v1/predict",
        files={"file": ("test_real.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "REAL"
    assert data["p_fake"] < 0.5
    assert data["duration_seconds"] == 3.0
    # 3.0 s audio @ 16kHz = 48,000 samples -> 1 + (48000 - 32000) // 8000 = 3 windows
    assert len(data["windows"]) == 3
    assert data["windows"][0]["t"] == 2.0
    assert data["windows"][1]["t"] == 2.5
    assert data["windows"][2]["t"] == 3.0


def test_predict_valid_wav_high_energy() -> None:
    # Amplitude 0.8 -> RMS ~= 0.56 > 0.25 -> Stub returns p_fake=0.88 (FAKE)
    wav_bytes = _generate_wav_bytes(duration_seconds=3.0, amplitude=0.8)

    response = client.post(
        "/api/v1/predict",
        files={"file": ("test_fake.wav", wav_bytes, "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "FAKE"
    assert data["p_fake"] >= 0.5
    assert len(data["windows"]) == 3


def test_predict_reject_empty_file() -> None:
    response = client.post(
        "/api/v1/predict",
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_predict_reject_unsupported_extension() -> None:
    response = client.post(
        "/api/v1/predict",
        files={"file": ("speech.pdf", b"dummy content", "application/pdf")},
    )
    assert response.status_code == 400
    assert "unsupported file format" in response.json()["detail"].lower()


def test_predict_reject_corrupt_audio_payload() -> None:
    response = client.post(
        "/api/v1/predict",
        files={
            "file": ("corrupt.wav", b"RIFF____WAVEfmt NOT_ACTUAL_AUDIO", "audio/wav")
        },
    )
    assert response.status_code == 400
    assert "failed to decode" in response.json()["detail"].lower()


def test_predict_reject_too_short_duration() -> None:
    # 1.0 s of audio < 2.0 s analysis window
    short_wav = _generate_wav_bytes(duration_seconds=1.0)
    response = client.post(
        "/api/v1/predict",
        files={"file": ("short.wav", short_wav, "audio/wav")},
    )
    assert response.status_code == 400
    assert "shorter than the minimum" in response.json()["detail"].lower()


def test_predict_reject_oversized_file() -> None:
    # 10 MB + 1 byte
    oversized_data = b"0" * (10 * 1024 * 1024 + 1)
    response = client.post(
        "/api/v1/predict",
        files={"file": ("huge.wav", oversized_data, "audio/wav")},
    )
    assert response.status_code == 413
    assert "exceeds" in response.json()["detail"].lower()
