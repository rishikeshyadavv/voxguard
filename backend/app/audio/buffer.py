"""Thread-safe in-memory ring buffer for audio streaming."""

import threading
from typing import Optional

import numpy as np


class RingBuffer:
    """A thread-safe circular buffer for mono float32 audio samples.

    Stores up to `capacity_seconds` of audio at `sample_rate`. When new
    samples exceed remaining capacity, oldest samples are evicted in FIFO order.
    """

    def __init__(
        self,
        capacity_seconds: float = 30.0,
        sample_rate: int = 16000,
    ) -> None:
        if capacity_seconds <= 0:
            raise ValueError("capacity_seconds must be positive")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")

        self.sample_rate = sample_rate
        self.capacity_samples = int(capacity_seconds * sample_rate)
        self._buffer: np.ndarray = np.zeros(self.capacity_samples, dtype=np.float32)
        self._size: int = 0
        self._head: int = 0  # Points to index where next sample will be written
        self._lock: threading.RLock = threading.RLock()

    @property
    def max_duration_seconds(self) -> float:
        """Maximum duration in seconds the buffer can hold."""
        return self.capacity_samples / self.sample_rate

    @property
    def duration_seconds(self) -> float:
        """Current duration of buffered audio in seconds."""
        with self._lock:
            return self._size / self.sample_rate

    def __len__(self) -> int:
        """Current number of buffered audio samples."""
        with self._lock:
            return self._size

    def append(self, samples: np.ndarray) -> None:
        """Append float32 audio samples to the ring buffer.

        If the number of samples exceeds capacity, only the most recent
        `capacity_samples` are retained.
        """
        if not isinstance(samples, np.ndarray):
            samples = np.asarray(samples, dtype=np.float32)
        elif samples.dtype != np.float32:
            samples = samples.astype(np.float32)

        if samples.ndim != 1:
            samples = samples.flatten()

        n = len(samples)
        if n == 0:
            return

        with self._lock:
            if n >= self.capacity_samples:
                # Discard everything and keep only the latest capacity_samples
                self._buffer[:] = samples[-self.capacity_samples :]
                self._size = self.capacity_samples
                self._head = 0
                return

            end = self._head + n
            if end <= self.capacity_samples:
                self._buffer[self._head : end] = samples
            else:
                first_part_len = self.capacity_samples - self._head
                self._buffer[self._head :] = samples[:first_part_len]
                self._buffer[: n - first_part_len] = samples[first_part_len:]

            self._head = (self._head + n) % self.capacity_samples
            self._size = min(self.capacity_samples, self._size + n)

    def get_all(self) -> np.ndarray:
        """Return a contiguous copy of all currently buffered samples."""
        with self._lock:
            if self._size == 0:
                return np.zeros(0, dtype=np.float32)

            start = (self._head - self._size) % self.capacity_samples
            if start + self._size <= self.capacity_samples:
                return self._buffer[start : start + self._size].copy()

            # Wrapped around the end of the circular buffer
            part1 = self._buffer[start:]
            part2 = self._buffer[: (start + self._size) % self.capacity_samples]
            return np.concatenate((part1, part2))

    def get_last(self, n_samples: int) -> np.ndarray:
        """Return the most recent `n_samples` from the buffer.

        If fewer samples are buffered, returns all available samples.
        """
        if n_samples < 0:
            raise ValueError("n_samples must be non-negative")
        with self._lock:
            if self._size == 0 or n_samples == 0:
                return np.zeros(0, dtype=np.float32)

            n = min(n_samples, self._size)
            all_samples = self.get_all()
            return all_samples[-n:].copy()

    def get_slice(self, start: int = 0, end: Optional[int] = None) -> np.ndarray:
        """Extract a slice of the buffered audio relative to the buffer start."""
        with self._lock:
            all_samples = self.get_all()
            return all_samples[start:end].copy()

    def clear(self) -> None:
        """Clear all contents in the ring buffer."""
        with self._lock:
            self._buffer.fill(0.0)
            self._size = 0
            self._head = 0
