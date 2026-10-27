"""Unit tests for HFEngine and Hugging Face deepfake detection."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
import torch

from app.inference.base import InferenceEngine
from app.inference.hf_engine import HFEngine


@pytest.fixture
def mock_hf_model_and_extractor():
    """Mock PyTorch model and feature extractor to avoid network downloads in tests."""
    # Config with id2label {0: "bonafide", 1: "spoof"}
    config = SimpleNamespace(id2label={0: "bonafide", 1: "spoof"})
    mock_model = MagicMock()
    mock_model.config = config
    mock_model.to.return_value = mock_model

    # Default forward returns equal logits
    mock_output = SimpleNamespace(logits=torch.tensor([[0.0, 0.0]]))
    mock_model.return_value = mock_output

    # Mock feature extractor returns dummy tensor dictionary
    mock_extractor = MagicMock()
    mock_extractor.return_value = {
        "input_values": torch.zeros((1, 32000), dtype=torch.float32)
    }

    return mock_model, mock_extractor


def test_hf_engine_protocol_conformance(mock_hf_model_and_extractor) -> None:
    model, extractor = mock_hf_model_and_extractor
    engine = HFEngine(
        model_name="test-spoof-model",
        device="cpu",
        model=model,
        feature_extractor=extractor,
    )

    assert isinstance(engine, InferenceEngine)
    assert engine.model_name == "test-spoof-model"
    assert engine.version == "1.0.0"


def test_hf_engine_label_resolution(mock_hf_model_and_extractor) -> None:
    model, extractor = mock_hf_model_and_extractor
    # Explicit mapping: 0=human, 1=synthetic
    model.config.id2label = {0: "human", 1: "synthetic"}

    engine = HFEngine(
        model_name="test-model",
        model=model,
        feature_extractor=extractor,
    )
    assert engine._fake_indices == [1]

    # Inverted mapping: 0=spoof, 1=bonafide
    model.config.id2label = {0: "spoof", 1: "bonafide"}
    engine2 = HFEngine(
        model_name="test-model-2",
        model=model,
        feature_extractor=extractor,
    )
    assert engine2._fake_indices == [0]


def test_hf_engine_predict_spoof_detection(mock_hf_model_and_extractor) -> None:
    model, extractor = mock_hf_model_and_extractor
    # id2label: 0 is bonafide, 1 is spoof
    model.config.id2label = {0: "bonafide", 1: "spoof"}

    # Mock strong spoof logit (index 1 is 10.0, index 0 is -10.0)
    model.return_value = SimpleNamespace(logits=torch.tensor([[-10.0, 10.0]]))

    engine = HFEngine(
        model_name="test-spoof",
        model=model,
        feature_extractor=extractor,
    )

    window = np.zeros(32000, dtype=np.float32)
    p_fake = engine.predict(window)

    assert 0.95 <= p_fake <= 1.0
    assert engine.last_latency_ms >= 0.0


def test_hf_engine_predict_bonafide_detection(mock_hf_model_and_extractor) -> None:
    model, extractor = mock_hf_model_and_extractor
    model.config.id2label = {0: "bonafide", 1: "spoof"}

    # Mock strong bonafide logit (index 0 is 10.0, index 1 is -10.0)
    model.return_value = SimpleNamespace(logits=torch.tensor([[10.0, -10.0]]))

    engine = HFEngine(
        model_name="test-bonafide",
        model=model,
        feature_extractor=extractor,
    )

    window = np.zeros(32000, dtype=np.float32)
    p_fake = engine.predict(window)

    assert 0.0 <= p_fake <= 0.05


def test_hf_engine_warmup(mock_hf_model_and_extractor) -> None:
    model, extractor = mock_hf_model_and_extractor
    engine = HFEngine(
        model_name="test-warmup",
        model=model,
        feature_extractor=extractor,
    )
    assert not engine.is_warmed_up

    engine.warmup()
    assert engine.is_warmed_up


def test_hf_engine_input_validation(mock_hf_model_and_extractor) -> None:
    model, extractor = mock_hf_model_and_extractor
    engine = HFEngine(
        model_name="test-validation",
        model=model,
        feature_extractor=extractor,
    )

    # Wrong length
    with pytest.raises(ValueError, match="Expected 32000 samples"):
        engine.predict(np.zeros(16000, dtype=np.float32))

    # NaNs
    nan_window = np.zeros(32000, dtype=np.float32)
    nan_window[0] = np.nan
    with pytest.raises(ValueError, match="NaN or Inf"):
        engine.predict(nan_window)
