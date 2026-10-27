"""Unit tests for the inference engine factory."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.config import settings
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


@patch("transformers.AutoModelForAudioClassification.from_pretrained")
@patch("transformers.AutoFeatureExtractor.from_pretrained")
def test_factory_hf_backend_success(mock_ext: object, mock_model: object) -> None:
    mock_model_inst = getattr(mock_model, "return_value")
    mock_model_inst.config = SimpleNamespace(id2label={0: "bonafide", 1: "spoof"})
    mock_model_inst.to.return_value = mock_model_inst

    engine = get_inference_engine("hf")
    assert isinstance(engine, InferenceEngine)
    assert engine.model_name == settings.hf_model_name


@patch(
    "transformers.AutoModelForAudioClassification.from_pretrained",
    side_effect=RuntimeError("Offline network mode"),
)
def test_factory_hf_fallback_to_stub(mock_model: object) -> None:
    engine = get_inference_engine("hf")
    assert isinstance(engine, StubEngine)


def test_factory_unknown_backend() -> None:
    with pytest.raises(ValueError, match="Unsupported inference backend"):
        get_inference_engine("quantum_onnx")
