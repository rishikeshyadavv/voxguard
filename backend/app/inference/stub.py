"""Deterministic stub inference engine for testing and UI development."""

import numpy as np

from app.inference.base import InferenceEngine, validate_audio_window


class StubEngine(InferenceEngine):
    """Deterministic inference engine implementing InferenceEngine protocol.

    Provides controllable modes (energy-based, fixed, and ramp) to allow
    reproducible unit, integration, and E2E dashboard testing without requiring
    heavy ML models or external downloads.
    """

    SUPPORTED_MODES = {"energy", "fixed", "ramp"}

    def __init__(
        self,
        mode: str = "energy",
        fixed_score: float = 0.15,
        energy_threshold: float = 0.25,
        ramp_step: float = 0.1,
    ) -> None:
        self._model_name = "stub"
        self._version = "0.1.0"
        self._mode = mode.lower()
        self._fixed_score = float(fixed_score)
        self._energy_threshold = float(energy_threshold)
        self._ramp_step = float(ramp_step)
        self._call_count = 0
        self.is_warmed_up = False

        if self._mode not in self.SUPPORTED_MODES:
            raise ValueError(
                f"Unsupported mode '{mode}'. Choose from {self.SUPPORTED_MODES}"
            )
        self._validate_score_bounds(self._fixed_score, "fixed_score")

    @property
    def model_name(self) -> str:
        """Name of the inference model."""
        return self._model_name

    @property
    def version(self) -> str:
        """Version string of the engine."""
        return self._version

    @property
    def mode(self) -> str:
        """Current evaluation mode."""
        return self._mode

    def set_mode(self, mode: str) -> None:
        """Switch the evaluation mode."""
        normalized = mode.lower()
        if normalized not in self.SUPPORTED_MODES:
            raise ValueError(
                f"Unsupported mode '{mode}'. Choose from {self.SUPPORTED_MODES}"
            )
        self._mode = normalized

    def set_fixed_score(self, score: float) -> None:
        """Set a fixed probability output and switch to 'fixed' mode."""
        val = float(score)
        self._validate_score_bounds(val, "score")
        self._fixed_score = val
        self._mode = "fixed"

    def set_energy_threshold(self, threshold: float) -> None:
        """Configure the RMS threshold used in energy mode."""
        if threshold < 0.0:
            raise ValueError("Energy threshold must be non-negative")
        self._energy_threshold = float(threshold)

    def predict(self, window: np.ndarray) -> float:
        """Evaluate deepfake probability p_fake for the provided audio window."""
        validate_audio_window(window)
        self._call_count += 1

        if self._mode == "fixed":
            return self._fixed_score

        if self._mode == "ramp":
            score = (self._call_count * self._ramp_step) % 1.0
            return float(np.clip(score, 0.0, 1.0))

        # Default mode: "energy"
        rms = float(np.sqrt(np.mean(window**2)))
        if rms >= self._energy_threshold:
            # High energy / synthetic signature -> high fake score
            return 0.88
        # Normal / ambient background speech -> low fake score
        return 0.12

    def warmup(self) -> None:
        """Preallocate memory or warm up stub structures."""
        self.is_warmed_up = True

    def reset(self) -> None:
        """Reset internal state and counter."""
        self._call_count = 0

    @staticmethod
    def _validate_score_bounds(score: float, param_name: str) -> None:
        if not (0.0 <= score <= 1.0):
            raise ValueError(f"{param_name} must be within [0.0, 1.0], got {score}")
