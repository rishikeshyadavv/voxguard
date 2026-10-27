"""Hugging Face pretrained audio classification deepfake detection engine."""

import logging
import time
from typing import Any, List, Optional, Set

import numpy as np
import torch
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

from app.config import settings
from app.inference.base import InferenceEngine, validate_audio_window

logger = logging.getLogger("voxguard.hf_engine")

# Known semantic substrings for synthetic / fake classes
FAKE_LABEL_SUBSTRINGS: Set[str] = {
    "spoof",
    "fake",
    "synthetic",
    "deepfake",
    "cloned",
    "generated",
    "ai",
}

# Known semantic substrings for genuine / human speech classes
REAL_LABEL_SUBSTRINGS: Set[str] = {
    "bonafide",
    "real",
    "human",
    "genuine",
    "natural",
}


class HFEngine(InferenceEngine):
    """Deepfake detection engine backed by Hugging Face audio classification models.

    Runs on CPU with explicit label mapping, feature extraction, and latency profiling.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        model: Optional[Any] = None,
        feature_extractor: Optional[Any] = None,
    ) -> None:
        self._model_name = model_name or settings.hf_model_name
        self._device_str = device or settings.hf_device
        self._device = torch.device(self._device_str)
        self._version = "1.0.0"

        self.last_latency_ms: float = 0.0
        self.is_warmed_up: bool = False

        # If model and feature extractor are injected (e.g. for testing)
        if model is not None and feature_extractor is not None:
            self.model = model
            self.feature_extractor = feature_extractor
        else:
            logger.info(
                "Loading HF audio model '%s' onto device '%s'",
                self._model_name,
                self._device_str,
            )
            self.feature_extractor = AutoFeatureExtractor.from_pretrained(  # type: ignore[no-untyped-call]
                self._model_name
            )
            self.model = AutoModelForAudioClassification.from_pretrained(
                self._model_name
            )

        self.model.to(self._device)
        self.model.eval()

        self._fake_indices: List[int] = self._resolve_fake_label_indices()

    @property
    def model_name(self) -> str:
        """Name of the Hugging Face model checkpoint."""
        return self._model_name

    @property
    def version(self) -> str:
        """Version string of the engine."""
        return self._version

    def _resolve_fake_label_indices(self) -> List[int]:
        """Resolve which output indices represent fake/spoofed audio from id2label."""
        id2label = getattr(self.model.config, "id2label", None)
        if not id2label:
            # Fallback assumption: index 1 is fake, index 0 is bonafide
            logger.warning("Model has no id2label mapping. Defaulting index 1 as fake.")
            return [1]

        fake_indices: List[int] = []
        for idx, raw_label in id2label.items():
            label = str(raw_label).lower()
            if any(sub in label for sub in FAKE_LABEL_SUBSTRINGS):
                fake_indices.append(int(idx))

        if not fake_indices:
            # If no explicit fake substring found, check for real and invert
            real_indices = [
                int(idx)
                for idx, raw in id2label.items()
                if any(sub in str(raw).lower() for sub in REAL_LABEL_SUBSTRINGS)
            ]
            if real_indices:
                fake_indices = [
                    int(idx) for idx in id2label if int(idx) not in real_indices
                ]

        if not fake_indices:
            # Default fallback if names cannot be categorized
            fake_indices = [1] if len(id2label) > 1 else [0]

        logger.info(
            "Resolved fake label indices %s for model '%s'",
            fake_indices,
            self._model_name,
        )
        return fake_indices

    def predict(self, window: np.ndarray) -> float:
        """Run deepfake inference on a 2.0 s audio window.

        Args:
            window: 1D float32 audio samples at 16 kHz.

        Returns:
            p_fake: Predicted deepfake probability strictly in [0.0, 1.0].
        """
        validate_audio_window(window)

        start_time = time.perf_counter()

        # Extract features
        inputs = self.feature_extractor(
            window,
            sampling_rate=settings.sample_rate,
            return_tensors="pt",
        )
        # Move tensors to target device
        inputs = {k: v.to(self._device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits

        # Compute softmax probabilities
        probs = torch.softmax(logits, dim=-1)[0]
        # Sum probability of fake indices
        fake_prob = sum(probs[i].item() for i in self._fake_indices)
        p_fake = float(np.clip(fake_prob, 0.0, 1.0))

        self.last_latency_ms = (time.perf_counter() - start_time) * 1000.0
        logger.debug(
            "Inference window processed in %.2f ms | p_fake: %.3f",
            self.last_latency_ms,
            p_fake,
        )

        return p_fake

    def warmup(self) -> None:
        """Run a zero-window pass to initialize compute kernels and cache."""
        dummy_window = np.zeros(
            int(settings.window_duration_seconds * settings.sample_rate),
            dtype=np.float32,
        )
        self.predict(dummy_window)
        self.is_warmed_up = True
        logger.info(
            "HF model warmed up successfully (latency: %.2f ms)",
            self.last_latency_ms,
        )
