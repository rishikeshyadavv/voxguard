"""Audio windowing and frame slicing utilities for streaming inference."""

from typing import Generator, List

import numpy as np


class Windower:
    """Slices streaming audio into fixed-length windows with hop overlap.

    Default configuration generates 2.0 s windows (32,000 samples at 16 kHz)
    with a 0.5 s hop (8,000 samples at 16 kHz), maintaining a carry-over
    buffer across incoming chunks of arbitrary size.
    """

    def __init__(
        self,
        window_duration_seconds: float = 2.0,
        hop_duration_seconds: float = 0.5,
        sample_rate: int = 16000,
    ) -> None:
        if window_duration_seconds <= 0:
            raise ValueError("window_duration_seconds must be positive")
        if hop_duration_seconds <= 0:
            raise ValueError("hop_duration_seconds must be positive")
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")

        self.sample_rate = sample_rate
        self.window_samples = int(round(window_duration_seconds * sample_rate))
        self.hop_samples = int(round(hop_duration_seconds * sample_rate))

        if self.hop_samples > self.window_samples:
            raise ValueError("hop_samples cannot exceed window_samples")

        self._carryover: np.ndarray = np.zeros(0, dtype=np.float32)

    @property
    def buffered_samples(self) -> int:
        """Number of partial samples currently waiting in carry-over."""
        return len(self._carryover)

    @property
    def buffered_duration_seconds(self) -> float:
        """Duration in seconds of audio waiting in carry-over."""
        return len(self._carryover) / self.sample_rate

    def process(self, chunk: np.ndarray) -> Generator[np.ndarray, None, None]:
        """Ingest an incoming audio chunk and yield all complete windows.

        Any remaining samples shorter than a full window are preserved in
        carry-over for the next chunk.
        """
        if not isinstance(chunk, np.ndarray):
            chunk = np.asarray(chunk, dtype=np.float32)
        elif chunk.dtype != np.float32:
            chunk = chunk.astype(np.float32)

        if chunk.ndim != 1:
            chunk = chunk.flatten()

        if len(chunk) == 0:
            return

        if len(self._carryover) > 0:
            data = np.concatenate((self._carryover, chunk))
        else:
            data = chunk

        n_samples = len(data)
        if n_samples < self.window_samples:
            self._carryover = data
            return

        start_idx = 0
        while start_idx + self.window_samples <= n_samples:
            window = data[start_idx : start_idx + self.window_samples]
            yield window.copy()
            start_idx += self.hop_samples

        self._carryover = data[start_idx:].copy()

    def add_chunk(self, chunk: np.ndarray) -> List[np.ndarray]:
        """Ingest chunk and return a list of complete windows."""
        return list(self.process(chunk))

    def reset(self) -> None:
        """Reset internal carry-over state."""
        self._carryover = np.zeros(0, dtype=np.float32)

    def clear(self) -> None:
        """Alias for reset."""
        self.reset()
