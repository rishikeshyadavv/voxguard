"""Unit tests for RingBuffer in app.audio.buffer."""

import concurrent.futures

import numpy as np
import pytest

from app.audio.buffer import RingBuffer


def test_initial_state() -> None:
    buf = RingBuffer(capacity_seconds=1.0, sample_rate=16000)
    assert len(buf) == 0
    assert buf.duration_seconds == 0.0
    assert buf.capacity_samples == 16000
    assert buf.max_duration_seconds == 1.0
    assert len(buf.get_all()) == 0


def test_append_and_retrieve_all() -> None:
    buf = RingBuffer(capacity_seconds=1.0, sample_rate=1000)
    samples = np.arange(100, dtype=np.float32)
    buf.append(samples)

    assert len(buf) == 100
    assert buf.duration_seconds == 0.1
    retrieved = buf.get_all()
    assert np.array_equal(retrieved, samples)


def test_overflow_eviction_fifo() -> None:
    # Buffer of size 10
    buf = RingBuffer(capacity_seconds=0.01, sample_rate=1000)
    assert buf.capacity_samples == 10

    # Append 8 samples: [0, 1, 2, ..., 7]
    buf.append(np.arange(8, dtype=np.float32))
    assert len(buf) == 8
    assert np.array_equal(buf.get_all(), np.arange(8, dtype=np.float32))

    # Append 5 more samples: [8, 9, 10, 11, 12]
    # Total appended = 13. Buffer capacity = 10.
    # Evicted oldest 3 ([0, 1, 2]). Remaining: [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    buf.append(np.arange(8, 13, dtype=np.float32))
    assert len(buf) == 10
    assert np.array_equal(buf.get_all(), np.arange(3, 13, dtype=np.float32))


def test_append_larger_than_capacity() -> None:
    buf = RingBuffer(capacity_seconds=0.01, sample_rate=1000)
    assert buf.capacity_samples == 10

    # Append 25 samples directly
    buf.append(np.arange(25, dtype=np.float32))
    assert len(buf) == 10
    # Should only retain the last 10 samples: [15, 16, ..., 24]
    assert np.array_equal(buf.get_all(), np.arange(15, 25, dtype=np.float32))


def test_get_last_and_slices() -> None:
    buf = RingBuffer(capacity_seconds=0.02, sample_rate=1000)  # 20 samples
    samples = np.arange(15, dtype=np.float32)
    buf.append(samples)

    # get_last
    last_5 = buf.get_last(5)
    assert np.array_equal(last_5, np.arange(10, 15, dtype=np.float32))

    # Request more samples than buffered
    last_30 = buf.get_last(30)
    assert np.array_equal(last_30, samples)

    # get_slice
    slice_mid = buf.get_slice(5, 10)
    assert np.array_equal(slice_mid, np.arange(5, 10, dtype=np.float32))


def test_clear() -> None:
    buf = RingBuffer(capacity_seconds=1.0, sample_rate=16000)
    buf.append(np.ones(1000, dtype=np.float32))
    assert len(buf) == 1000

    buf.clear()
    assert len(buf) == 0
    assert buf.duration_seconds == 0.0
    assert len(buf.get_all()) == 0


def test_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="capacity_seconds must be positive"):
        RingBuffer(capacity_seconds=0, sample_rate=16000)

    with pytest.raises(ValueError, match="sample_rate must be positive"):
        RingBuffer(capacity_seconds=1.0, sample_rate=-10)

    buf = RingBuffer(capacity_seconds=1.0, sample_rate=16000)
    with pytest.raises(ValueError, match="n_samples must be non-negative"):
        buf.get_last(-1)


def test_multithreaded_appends() -> None:
    buf = RingBuffer(capacity_seconds=1.0, sample_rate=16000)

    def worker(val: float) -> None:
        chunk = np.full(50, val, dtype=np.float32)
        for _ in range(20):
            buf.append(chunk)

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, float(i)) for i in range(8)]
        for f in futures:
            f.result()

    # 8 workers * 20 iterations * 50 samples = 8000 samples
    assert len(buf) == 8000
    assert buf.duration_seconds == 0.5
