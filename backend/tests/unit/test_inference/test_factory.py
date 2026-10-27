"""Unit tests for the inference engine factory."""

import pytest

from app.inference.base import InferenceEngine
from app.inference.factory import get_inference_engine
from app.inference.stub import StubEngine


def test_factory_default_stub() -> None:
    engine = get_inference_engine()
    assert isinstance(engine, StubEngine)
    assert isinstance(engine, InferenceEngine)
    assert engine.model_name == "stub"


def test_factory_explicit_stub() -> None:
    engine = get_inference_engine("stub")
    assert isinstance(engine, StubEngine)

    # Case-insensitive
    engine_upper = get_inference_engine("STUB")
    assert isinstance(engine_upper, StubEngine)


def test_factory_hf_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="Step 6"):
        get_inference_engine("hf")


def test_factory_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unsupported inference backend"):
        get_inference_engine("quantum_onnx")
