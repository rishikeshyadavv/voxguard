"""Inference engine factory for VoxGuard."""

import logging
from typing import Optional

from app.config import settings
from app.inference.base import InferenceEngine
from app.inference.stub import StubEngine

logger = logging.getLogger("voxguard.inference_factory")


def get_inference_engine(backend: Optional[str] = None) -> InferenceEngine:
    """Create and return an InferenceEngine instance according to configuration.

    Args:
        backend: Engine name ("stub", "hf"). If omitted, defaults to
                 settings.model_backend.

    Returns:
        An instance conforming to the InferenceEngine Protocol.
    """
    engine_type = (backend or settings.model_backend).strip().lower()

    if engine_type == "stub":
        return StubEngine()

    if engine_type == "hf":
        try:
            from app.inference.hf_engine import HFEngine

            return HFEngine()
        except Exception as exc:
            logger.warning(
                "Failed to initialize Hugging Face engine ('%s'): %s. "
                "Falling back to StubEngine.",
                settings.hf_model_name,
                exc,
            )
            return StubEngine()

    raise ValueError(
        f"Unsupported inference backend '{engine_type}'. "
        "Supported backends: 'stub', 'hf'"
    )
