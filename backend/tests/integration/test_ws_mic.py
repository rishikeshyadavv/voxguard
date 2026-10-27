"""Integration tests for WebSocket /ws/mic audio streaming."""

import numpy as np
from fastapi.testclient import TestClient

from app.audio.io import encode_pcm16
from app.main import app

client = TestClient(app)


def _synthesize_pcm16_chunk(
    duration_seconds: float = 1.0,
    amplitude: float = 0.1,
    sample_rate: int = 16000,
) -> bytes:
    """Generate synthesized PCM16 bytes."""
    n_samples = int(duration_seconds * sample_rate)
    t = np.linspace(0, duration_seconds, n_samples, endpoint=False, dtype=np.float32)
    samples = amplitude * np.sin(2 * np.pi * 440 * t)
    return encode_pcm16(samples)


def test_ws_handshake_and_error_handling() -> None:
    with client.websocket_connect("/ws/mic") as ws:
        # Valid sample rate
        ws.send_text('{"sample_rate": 16000}')

        # Invalid sample rate error
        ws.send_text('{"sample_rate": 44100}')
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "44100" in msg["message"]

        # Malformed JSON error
        ws.send_text("not_valid_json_string{")
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "Malformed JSON" in msg["message"]

        # Odd byte count PCM error
        ws.send_bytes(b"\x00\x01\x02")
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "PCM decode error" in msg["message"]


def test_ws_streaming_irregular_chunk_sizes() -> None:
    # 4.0 seconds of low-energy audio @ 16 kHz = 64,000 samples = 128,000 bytes
    total_pcm = _synthesize_pcm16_chunk(duration_seconds=4.0, amplitude=0.08)

    with client.websocket_connect("/ws/mic") as ws:
        # Stream in arbitrary irregular even chunk sizes (2 bytes per sample)
        chunk_sizes = [512, 1024, 750, 3112, 4000]
        offset = 0
        chunk_idx = 0
        while offset < len(total_pcm):
            size = chunk_sizes[chunk_idx % len(chunk_sizes)]
            chunk = total_pcm[offset : offset + size]
            offset += len(chunk)
            ws.send_bytes(chunk)
            chunk_idx += 1

        # 4.0 s audio -> windows at 2.0s, 2.5s, 3.0s, 3.5s, 4.0s = 5 windows
        score_messages = []
        for _ in range(5):
            msg = ws.receive_json()
            assert msg["type"] == "score"
            assert msg["state"] == "NORMAL"
            assert 0.0 <= msg["p_fake"] <= 0.2
            assert 0.0 <= msg["p_smooth"] <= 0.2
            score_messages.append(msg)

        assert len(score_messages) == 5
        assert score_messages[0]["t"] == 2.0
        assert score_messages[1]["t"] == 2.5
        assert score_messages[2]["t"] == 3.0
        assert score_messages[3]["t"] == 3.5
        assert score_messages[4]["t"] == 4.0


def test_ws_alert_triggering_on_high_fake() -> None:
    # High amplitude audio: 0.8 -> RMS ~= 0.56 > 0.25 -> Stub returns p_fake=0.88
    # 6.0 seconds of audio -> 1 + (96000 - 32000) // 8000 = 9 windows
    high_fake_pcm = _synthesize_pcm16_chunk(duration_seconds=6.0, amplitude=0.8)

    with client.websocket_connect("/ws/mic") as ws:
        # Ingest in 8000-byte chunks
        chunk_size = 8000
        for i in range(0, len(high_fake_pcm), chunk_size):
            ws.send_bytes(high_fake_pcm[i : i + chunk_size])

        # 9 windows yield 9 score frames + exactly 1 alert frame = 10 frames
        messages = [ws.receive_json() for _ in range(10)]
        score_msgs = [m for m in messages if m["type"] == "score"]
        alert_msgs = [m for m in messages if m["type"] == "alert"]

        assert len(score_msgs) == 9
        assert len(alert_msgs) == 1
        assert alert_msgs[0]["p_smooth"] >= 0.75
        assert alert_msgs[0]["t"] == 3.0  # Emitted on 3rd window (at 3.0 s)


def test_ws_abrupt_disconnect() -> None:
    # Connect, send partial data, and abruptly close connection
    with client.websocket_connect("/ws/mic") as ws:
        partial_pcm = _synthesize_pcm16_chunk(duration_seconds=0.5)
        ws.send_bytes(partial_pcm)
    # Context manager exit closes the socket. Verify server handled it cleanly.
