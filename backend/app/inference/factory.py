"""Inference engine factory for VoxGuard."""

from typing import Optional

from app.config import settings
from app.inference.base import InferenceEngine
from app.inference.stub import StubEngine


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
        raise NotImplementedError(
            "Hugging Face engine ('hf') will be implemented in Step 6. "
            "Use 'stub' for current prototype milestones."
        )

    raise ValueError(
        f"Unsupported inference backend '{engine_type}'. "
        "Supported backends: 'stub', 'hf'"
    )
