"""Unit tests for Windower in app.audio.windowing."""

import numpy as np
import pytest

from app.audio.windowing import Windower


def test_window_counts_known_duration() -> None:
    # 2.0 s window (32,000 samples), 0.5 s hop (8,000 samples) at 16,000 Hz
    windower = Windower(
        window_duration_seconds=2.0, hop_duration_seconds=0.5, sample_rate=16000
    )

    # 1.5 s of audio (24,000 samples) -> 0 windows, 24,000 samples in carryover
    chunk_1_5s = np.zeros(24000, dtype=np.float32)
    windows = windower.add_chunk(chunk_1_5s)
    assert len(windows) == 0
    assert windower.buffered_samples == 24000

    # Feed another 0.5 s (8,000 samples) -> total 32,000 samples -> 1 window
    # After yielding window 1, carryover is 32000 - 8000 = 24,000 samples
    chunk_0_5s = np.zeros(8000, dtype=np.float32)
    windows2 = windower.add_chunk(chunk_0_5s)
    assert len(windows2) == 1
    assert windows2[0].shape == (32000,)
    assert windower.buffered_samples == 24000

    # Feed another 0.5 s (8,000 samples) -> total 32,000 samples -> 1 window
    windows3 = windower.add_chunk(chunk_0_5s)
    assert len(windows3) == 1


def test_exact_window_count_for_long_stream() -> None:
    windower = Windower(
        window_duration_seconds=2.0, hop_duration_seconds=0.5, sample_rate=16000
    )
    # 5.0 seconds of audio = 80,000 samples
    # Expected windows: 1 + (80000 - 32000) // 8000 = 1 + 6 = 7 windows
    long_audio = np.arange(80000, dtype=np.float32)
    windows = windower.add_chunk(long_audio)

    assert len(windows) == 7
    for i, w in enumerate(windows):
        assert len(w) == 32000
        expected_start = i * 8000
        assert np.array_equal(w, long_audio[expected_start : expected_start + 32000])


def test_hop_shifts_and_overlap_math() -> None:
    windower = Windower(
        window_duration_seconds=2.0, hop_duration_seconds=0.5, sample_rate=1000
    )
    # Window = 2000 samples, Hop = 500 samples
    audio = np.arange(4000, dtype=np.float32)
    windows = windower.add_chunk(audio)

    # 1 + (4000 - 2000) // 500 = 5 windows
    assert len(windows) == 5

    # Verify window[1] overlaps with window[0] by exactly 1500 samples
    assert np.array_equal(windows[0][500:], windows[1][:1500])
    assert np.array_equal(windows[1][500:], windows[2][:1500])


def test_odd_chunk_sizes_consistency() -> None:
    windower_single = Windower(
        window_duration_seconds=1.0, hop_duration_seconds=0.25, sample_rate=1000
    )
    windower_stream = Windower(
        window_duration_seconds=1.0, hop_duration_seconds=0.25, sample_rate=1000
    )

    total_samples = 5000
    audio = np.random.randn(total_samples).astype(np.float32)

    # Ingest in one go
    expected_windows = windower_single.add_chunk(audio)

    # Ingest in weird arbitrary chunk sizes: 1, 137, 513, 17, 3000...
    chunk_sizes = [1, 137, 513, 17, 1000, 200, 332, 800, 1000]
    streamed_windows = []
    idx = 0
    for size in chunk_sizes:
        if idx >= total_samples:
            break
        chunk = audio[idx : idx + size]
        idx += size
        for w in windower_stream.process(chunk):
            streamed_windows.append(w)

    if idx < total_samples:
        for w in windower_stream.process(audio[idx:]):
            streamed_windows.append(w)

    assert len(streamed_windows) == len(expected_windows)
    for sw, ew in zip(streamed_windows, expected_windows):
        assert np.allclose(sw, ew)


def test_reset_and_clear() -> None:
    windower = Windower(
        window_duration_seconds=2.0, hop_duration_seconds=0.5, sample_rate=16000
    )
    windower.add_chunk(np.zeros(20000, dtype=np.float32))
    assert windower.buffered_samples == 20000

    windower.reset()
    assert windower.buffered_samples == 0
    assert windower.buffered_duration_seconds == 0.0


def test_invalid_windower_parameters() -> None:
    with pytest.raises(ValueError, match="window_duration_seconds must be positive"):
        Windower(window_duration_seconds=-1.0)

    with pytest.raises(ValueError, match="hop_duration_seconds must be positive"):
        Windower(hop_duration_seconds=0)

    with pytest.raises(ValueError, match="hop_samples cannot exceed window_samples"):
        Windower(window_duration_seconds=1.0, hop_duration_seconds=2.0)
