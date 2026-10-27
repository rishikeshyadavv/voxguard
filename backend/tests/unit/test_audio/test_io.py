"""Unit tests for audio ingest and decode utilities in app.audio.io."""

import io

import numpy as np
import pytest
import soundfile as sf

from app.audio.io import decode_pcm16, encode_pcm16, load_audio_file


def test_decode_pcm16_empty() -> None:
    result = decode_pcm16(b"")
    assert isinstance(result, np.ndarray)
    assert len(result) == 0
    assert result.dtype == np.float32


def test_decode_pcm16_odd_length() -> None:
    with pytest.raises(ValueError, match="multiple of 2 bytes"):
        decode_pcm16(b"\x00\x00\x00")


def test_decode_pcm16_boundary_values() -> None:
    # 0 -> 0.0
    # 32767 (0x7FFF) -> 32767 / 32768 ~= 0.9999695
    # -32768 (0x8000) -> -32768 / 32768 = -1.0
    pcm_bytes = b"\x00\x00\xff\x7f\x00\x80"
    decoded = decode_pcm16(pcm_bytes)

    assert len(decoded) == 3
    assert decoded.dtype == np.float32
    assert decoded[0] == pytest.approx(0.0, abs=1e-5)
    assert decoded[1] == pytest.approx(32767.0 / 32768.0, abs=1e-5)
    assert decoded[2] == pytest.approx(-1.0, abs=1e-5)


def test_pcm16_round_trip() -> None:
    # Generate random audio in [-1.0, 1.0]
    np.random.seed(42)
    original = np.random.uniform(-1.0, 1.0, 10000).astype(np.float32)

    encoded = encode_pcm16(original)
    assert len(encoded) == 10000 * 2

    recovered = decode_pcm16(encoded)
    assert len(recovered) == 10000
    # Maximum 16-bit quantization error is 1 / 32768
    max_error = np.max(np.abs(original - recovered))
    assert max_error <= (1.0 / 32768.0) + 1e-6


def test_load_audio_file_empty_and_corrupt() -> None:
    with pytest.raises(ValueError, match="empty"):
        load_audio_file(b"")

    with pytest.raises(ValueError, match="Failed to decode audio file"):
        load_audio_file(b"NOT_A_VALID_AUDIO_FILE_HEADER_XYZ")


def test_load_audio_file_mono_wav() -> None:
    sr = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    sine_wave = 0.5 * np.sin(2 * np.pi * 440 * t)

    buf = io.BytesIO()
    sf.write(buf, sine_wave, sr, format="WAV")
    wav_bytes = buf.getvalue()

    loaded = load_audio_file(wav_bytes, target_sr=16000)
    assert len(loaded) == sr
    assert loaded.dtype == np.float32
    assert np.allclose(loaded, sine_wave, atol=1e-4)


def test_load_audio_file_stereo_downmix() -> None:
    sr = 16000
    duration = 0.5
    n_samples = int(sr * duration)
    # Left channel = 0.6, Right channel = -0.2 -> Mono average = 0.2
    left = np.full(n_samples, 0.6, dtype=np.float32)
    right = np.full(n_samples, -0.2, dtype=np.float32)
    stereo = np.column_stack((left, right))

    buf = io.BytesIO()
    sf.write(buf, stereo, sr, format="WAV")
    stereo_bytes = buf.getvalue()

    loaded = load_audio_file(stereo_bytes, target_sr=16000)
    assert loaded.ndim == 1
    assert len(loaded) == n_samples
    assert np.allclose(loaded, 0.2, atol=1e-4)


def test_load_audio_file_resampling_frequency_preservation() -> None:
    # 44.1 kHz input resampled to 16 kHz target
    input_sr = 44100
    target_sr = 16000
    target_freq = 1000.0  # 1 kHz test tone
    duration = 1.0
    t = np.linspace(
        0, duration, int(input_sr * duration), endpoint=False, dtype=np.float32
    )
    tone = 0.8 * np.sin(2 * np.pi * target_freq * t)

    buf = io.BytesIO()
    sf.write(buf, tone, input_sr, format="WAV")
    file_bytes = buf.getvalue()

    resampled = load_audio_file(file_bytes, target_sr=target_sr)
    assert len(resampled) == target_sr
    assert resampled.dtype == np.float32

    # Verify 1 kHz tone peak in FFT
    fft_magnitudes = np.abs(np.fft.rfft(resampled))
    fft_freqs = np.fft.rfftfreq(len(resampled), d=1.0 / target_sr)
    peak_freq = fft_freqs[np.argmax(fft_magnitudes)]

    assert abs(peak_freq - target_freq) < 5.0  # Within 5 Hz resolution
