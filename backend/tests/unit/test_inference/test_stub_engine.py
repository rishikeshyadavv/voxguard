"""Unit tests for StubEngine and InferenceEngine protocol validation."""

import numpy as np
import pytest

from app.inference.base import InferenceEngine
from app.inference.stub import StubEngine


@pytest.fixture
def valid_silence_window() -> np.ndarray:
    return np.zeros(32000, dtype=np.float32)


@pytest.fixture
def valid_high_energy_window() -> np.ndarray:
    # Sine wave with high amplitude 0.8 -> RMS ~= 0.8 / sqrt(2) ~= 0.565 > 0.25
    t = np.linspace(0, 2.0, 32000, endpoint=False, dtype=np.float32)
    return 0.8 * np.sin(2 * np.pi * 440 * t)


def test_protocol_conformance() -> None:
    engine = StubEngine()
    assert isinstance(engine, InferenceEngine)
    assert engine.model_name == "stub"
    assert engine.version == "0.1.0"


def test_input_validation_types_and_dimensions() -> None:
    engine = StubEngine()

    # Reject non-numpy array
    with pytest.raises(TypeError, match="numpy ndarray"):
        engine.predict([0.0] * 32000)  # type: ignore[arg-type]

    # Reject 2D array
    with pytest.raises(ValueError, match="Expected 1D audio window"):
        engine.predict(np.zeros((1, 32000), dtype=np.float32))

    # Reject non-float32
    with pytest.raises(ValueError, match="Expected float32 dtype"):
        engine.predict(np.zeros(32000, dtype=np.float64))

    # Reject incorrect sample length
    with pytest.raises(ValueError, match="Expected 32000 samples"):
        engine.predict(np.zeros(16000, dtype=np.float32))

    # Reject empty array
    with pytest.raises(ValueError, match="Audio window cannot be empty"):
        engine.predict(np.zeros(0, dtype=np.float32))


def test_input_validation_nan_and_inf(valid_silence_window: np.ndarray) -> None:
    engine = StubEngine()

    # Test NaN
    nan_window = valid_silence_window.copy()
    nan_window[100] = np.nan
    with pytest.raises(ValueError, match="NaN or Inf"):
        engine.predict(nan_window)

    # Test Inf
    inf_window = valid_silence_window.copy()
    inf_window[500] = np.inf
    with pytest.raises(ValueError, match="NaN or Inf"):
        engine.predict(inf_window)


def test_energy_mode_deterministic_outputs(
    valid_silence_window: np.ndarray,
    valid_high_energy_window: np.ndarray,
) -> None:
    engine = StubEngine(mode="energy", energy_threshold=0.25)

    # Silence (RMS = 0.0) -> low fake score (0.12 <= 0.15)
    score_low = engine.predict(valid_silence_window)
    assert 0.0 <= score_low <= 0.15
    assert score_low == pytest.approx(0.12)

    # High energy (RMS ~= 0.56 > 0.25) -> high fake score (0.88 >= 0.85)
    score_high = engine.predict(valid_high_energy_window)
    assert 0.85 <= score_high <= 1.0
    assert score_high == pytest.approx(0.88)


def test_fixed_score_mode(valid_silence_window: np.ndarray) -> None:
    engine = StubEngine()

    engine.set_fixed_score(0.72)
    assert engine.mode == "fixed"
    assert engine.predict(valid_silence_window) == pytest.approx(0.72)

    engine.set_fixed_score(0.0)
    assert engine.predict(valid_silence_window) == pytest.approx(0.0)

    engine.set_fixed_score(1.0)
    assert engine.predict(valid_silence_window) == pytest.approx(1.0)

    # Reject out-of-bounds scores
    with pytest.raises(ValueError, match="must be within"):
        engine.set_fixed_score(-0.01)

    with pytest.raises(ValueError, match="must be within"):
        engine.set_fixed_score(1.05)


def test_ramp_mode(valid_silence_window: np.ndarray) -> None:
    engine = StubEngine(mode="ramp", ramp_step=0.2)

    # Call ramp 5 times
    s1 = engine.predict(valid_silence_window)
    s2 = engine.predict(valid_silence_window)
    s3 = engine.predict(valid_silence_window)

    assert 0.0 <= s1 <= 1.0
    assert 0.0 <= s2 <= 1.0
    assert 0.0 <= s3 <= 1.0
    assert s2 > s1
    assert s3 > s2


def test_warmup_and_reset(valid_silence_window: np.ndarray) -> None:
    engine = StubEngine()
    assert not engine.is_warmed_up

    engine.warmup()
    assert engine.is_warmed_up

    engine.predict(valid_silence_window)
    assert engine._call_count == 1

    engine.reset()
    assert engine._call_count == 0


def test_invalid_mode_handling() -> None:
    with pytest.raises(ValueError, match="Unsupported mode"):
        StubEngine(mode="magic_model")

    engine = StubEngine()
    with pytest.raises(ValueError, match="Unsupported mode"):
        engine.set_mode("invalid_mode")
