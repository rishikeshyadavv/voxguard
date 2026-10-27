"""Audio input/output conversion and file decoding utilities."""

import io
from typing import Optional, cast

import numpy as np
import soundfile as sf
import soxr


def decode_pcm16(data: bytes) -> np.ndarray:
    """Decode raw little-endian 16-bit signed PCM bytes into normalized float32.

    Returns a 1D float32 numpy array with values strictly bounded in [-1.0, 1.0].
    An empty bytes payload returns an empty float32 array.
    """
    if len(data) == 0:
        return np.zeros(0, dtype=np.float32)

    if len(data) % 2 != 0:
        raise ValueError("PCM16 data length must be a multiple of 2 bytes")

    int_samples = np.frombuffer(data, dtype="<i2").astype(np.float32)
    normalized = int_samples / 32768.0
    return cast(np.ndarray, np.clip(normalized, -1.0, 1.0))


def encode_pcm16(samples: np.ndarray) -> bytes:
    """Encode normalized float32 audio in [-1.0, 1.0] to little-endian PCM16 bytes.

    Useful for streaming simulation and test fixture synthesis.
    """
    if not isinstance(samples, np.ndarray):
        samples = np.asarray(samples, dtype=np.float32)
    elif samples.dtype != np.float32:
        samples = samples.astype(np.float32)

    if samples.ndim != 1:
        samples = samples.flatten()

    clipped = np.clip(samples, -1.0, 1.0)
    # Scale to 16-bit signed range [-32768, 32767]
    scaled = np.clip(np.round(clipped * 32768.0), -32768.0, 32767.0).astype("<i2")
    return bytes(scaled.tobytes())


def load_audio_file(
    file_bytes: bytes,
    target_sr: int = 16000,
    quality: Optional[str] = "HQ",
) -> np.ndarray:
    """Decode audio file bytes (wav, mp3, flac, ogg) to 16 kHz mono float32.

    Reads audio file from memory using SoundFile, downmixes multi-channel audio
    to mono, and resamples to target_sr using soxr.
    """
    if not file_bytes:
        raise ValueError("Audio file payload is empty")

    if target_sr <= 0:
        raise ValueError("target_sr must be positive")

    try:
        buffer = io.BytesIO(file_bytes)
        data, sr = sf.read(buffer, dtype="float32")
    except Exception as exc:
        raise ValueError(f"Failed to decode audio file payload: {exc}") from exc

    if data.ndim > 1:
        # Multi-channel audio: average across channels to downmix to mono
        data = data.mean(axis=1).astype(np.float32)

    if sr != target_sr:
        data = soxr.resample(data, in_rate=sr, out_rate=target_sr, quality=quality)

    return np.ascontiguousarray(data, dtype=np.float32)
