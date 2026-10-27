"""Unit tests for ScoreSmoother in app.decision.smoothing."""

import pytest

from app.decision.smoothing import ScoreSmoother


def test_initial_state() -> None:
    smoother = ScoreSmoother(window_size=5)
    assert len(smoother) == 0
    assert smoother.current_score == 0.0
    assert smoother.scores == []


def test_partial_window_average() -> None:
    smoother = ScoreSmoother(window_size=4)

    # 1 score: mean = 0.4
    s1 = smoother.append(0.4)
    assert s1 == pytest.approx(0.4)
    assert len(smoother) == 1

    # 2 scores: mean = (0.4 + 0.6) / 2 = 0.5
    s2 = smoother.append(0.6)
    assert s2 == pytest.approx(0.5)
    assert len(smoother) == 2

    # 3 scores: mean = (0.4 + 0.6 + 0.8) / 3 = 0.6
    s3 = smoother.append(0.8)
    assert s3 == pytest.approx(0.6)
    assert len(smoother) == 3


def test_fifo_overflow_eviction() -> None:
    smoother = ScoreSmoother(window_size=3)

    smoother.append(0.1)
    smoother.append(0.2)
    smoother.append(0.3)
    assert smoother.current_score == pytest.approx(0.2)
    assert smoother.scores == [0.1, 0.2, 0.3]

    # Append 4th score: 0.1 evicted, remaining [0.2, 0.3, 1.0] -> mean = 0.5
    res = smoother.append(1.0)
    assert len(smoother) == 3
    assert smoother.scores == [0.2, 0.3, 1.0]
    assert res == pytest.approx(0.5)


def test_reset_and_clear() -> None:
    smoother = ScoreSmoother(window_size=4)
    smoother.append(0.9)
    smoother.append(0.8)
    assert len(smoother) == 2

    smoother.reset()
    assert len(smoother) == 0
    assert smoother.current_score == 0.0
    assert smoother.scores == []


def test_invalid_window_size() -> None:
    with pytest.raises(ValueError, match="window_size must be positive"):
        ScoreSmoother(window_size=0)

    with pytest.raises(ValueError, match="window_size must be positive"):
        ScoreSmoother(window_size=-5)
