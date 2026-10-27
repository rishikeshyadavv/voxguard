"""Inference engine protocol abstraction for voice deepfake detection."""

from typing import Optional, Protocol, runtime_checkable

import numpy as np


def validate_audio_window(
    window: np.ndarray, expected_samples: Optional[int] = 32000
) -> None:
    """Validate audio window format: 1D float32 array without NaNs or Infs."""
    if not isinstance(window, np.ndarray):
        raise TypeError("Audio window must be a numpy ndarray")
    if window.ndim != 1:
        raise ValueError(f"Expected 1D audio window, got ndim={window.ndim}")
    if window.dtype != np.float32:
        raise ValueError(f"Expected float32 dtype, got {window.dtype}")
    if len(window) == 0:
        raise ValueError("Audio window cannot be empty")
    if expected_samples is not None and len(window) != expected_samples:
        raise ValueError(
            f"Expected {expected_samples} samples (2.0s @ 16kHz), got {len(window)}"
        )
    if not np.isfinite(window).all():
        raise ValueError("Audio window contains NaN or Inf values")


@runtime_checkable
class InferenceEngine(Protocol):
    """Protocol interface that all deepfake detection models must satisfy."""

    @property
    def model_name(self) -> str:
        """Name of the inference model or stub."""
        ...

    @property
    def version(self) -> str:
        """Version string of the model or engine implementation."""
        ...

    def predict(self, window: np.ndarray) -> float:
        """Predict the deepfake probability p_fake for a single audio window.

        Args:
            window: 1D float32 numpy array with values in [-1.0, 1.0] at 16 kHz.

        Returns:
            p_fake: Probability of synthetic speech bounded in [0.0, 1.0].
        """
        ...

    def warmup(self) -> None:
        """Warm up engine and preallocate required compute resources."""
        ...
