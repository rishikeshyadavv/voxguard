"""Unit and property-based tests for StateMachine in app.decision.state_machine."""

from typing import List

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.decision.state_machine import CallState, StateMachine


def test_initial_state() -> None:
    sm = StateMachine()
    assert sm.state == CallState.NORMAL
    assert sm.consecutive_alerts == 0
    assert not sm.alert_emitted
    assert not sm.session_alert_emitted


def test_standard_transitions_normal_suspicious_alert_normal() -> None:
    # Default: t_suspicious=0.5, t_alert=0.75, alert_consecutive=3, clear_threshold=0.4
    sm = StateMachine(
        t_suspicious=0.5,
        t_alert=0.75,
        consecutive_alert_count=3,
        clear_threshold=0.4,
    )

    # 1. NORMAL: score = 0.2
    u1 = sm.update(0.2)
    assert u1.state == CallState.NORMAL
    assert not u1.alert_triggered

    # 2. Transition to SUSPICIOUS: score = 0.55
    u2 = sm.update(0.55)
    assert u2.state == CallState.SUSPICIOUS
    assert not u2.alert_triggered

    # 3. Alert score 1: score = 0.8 -> still SUSPICIOUS (consecutive=1)
    u3 = sm.update(0.8)
    assert u3.state == CallState.SUSPICIOUS
    assert sm.consecutive_alerts == 1
    assert not u3.alert_triggered

    # 4. Alert score 2: score = 0.85 -> still SUSPICIOUS (consecutive=2)
    u4 = sm.update(0.85)
    assert u4.state == CallState.SUSPICIOUS
    assert sm.consecutive_alerts == 2
    assert not u4.alert_triggered

    # 5. Transition to ALERT: score = 0.9 (consecutive=3)
    u5 = sm.update(0.9)
    assert u5.state == CallState.ALERT
    assert sm.consecutive_alerts == 3
    assert u5.alert_triggered
    assert sm.alert_emitted
    assert sm.session_alert_emitted

    # 6. Score remains high: score = 0.95 -> still ALERT, but alert_triggered is False
    u6 = sm.update(0.95)
    assert u6.state == CallState.ALERT
    assert not u6.alert_triggered  # No duplicate alert spam

    # 7. Transition back to NORMAL: score = 0.35 (< clear_threshold 0.4)
    u7 = sm.update(0.35)
    assert u7.state == CallState.NORMAL
    assert not sm.alert_emitted  # Cycle reset
    assert sm.session_alert_emitted  # Session history preserved


def test_hysteresis_does_not_clear_above_threshold() -> None:
    sm = StateMachine(
        t_suspicious=0.5,
        t_alert=0.75,
        consecutive_alert_count=3,
        clear_threshold=0.4,
    )

    # Elevate to SUSPICIOUS
    sm.update(0.6)
    assert sm.state == CallState.SUSPICIOUS

    # Score drops to 0.45: below t_suspicious (0.5), but above clear_threshold (0.4)
    # Hysteresis must keep it in SUSPICIOUS
    u = sm.update(0.45)
    assert u.state == CallState.SUSPICIOUS

    # Score drops to 0.39 (< 0.4): drops to NORMAL
    u_clear = sm.update(0.39)
    assert u_clear.state == CallState.NORMAL


def test_consecutive_interruption_resets_counter() -> None:
    sm = StateMachine(
        t_suspicious=0.5,
        t_alert=0.75,
        consecutive_alert_count=3,
        clear_threshold=0.4,
    )

    sm.update(0.8)  # consecutive=1
    sm.update(0.8)  # consecutive=2
    assert sm.consecutive_alerts == 2

    # Interrupt with 0.74 (< 0.75)
    sm.update(0.74)
    assert sm.consecutive_alerts == 0
    assert sm.state == CallState.SUSPICIOUS

    # Next 0.8 starts from consecutive=1 again
    sm.update(0.8)
    assert sm.consecutive_alerts == 1
    assert sm.state == CallState.SUSPICIOUS


def test_invalid_thresholds() -> None:
    # suspicious >= alert
    with pytest.raises(ValueError, match="Invalid threshold ordering"):
        StateMachine(t_suspicious=0.8, t_alert=0.7)

    # clear >= suspicious
    with pytest.raises(ValueError, match="Invalid threshold ordering"):
        StateMachine(t_suspicious=0.5, clear_threshold=0.6)

    # consecutive count < 1
    with pytest.raises(ValueError, match="consecutive_alert_count"):
        StateMachine(consecutive_alert_count=0)


# =========================================================================
# Property-based testing with Hypothesis
# =========================================================================


@given(
    scores=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=1,
        max_size=60,
    )
)
def test_hypothesis_alert_never_reached_without_consecutive_count(
    scores: List[float],
) -> None:
    """Invariant: ALERT is unreachable in fewer than consecutive_alert_count steps."""
    consecutive_required = 3
    sm = StateMachine(
        t_suspicious=0.5,
        t_alert=0.75,
        consecutive_alert_count=consecutive_required,
        clear_threshold=0.4,
    )

    alert_reached_step = None
    for step_idx, score in enumerate(scores):
        update = sm.update(score)
        if update.state == CallState.ALERT:
            alert_reached_step = step_idx
            break

    if alert_reached_step is not None:
        # Step index is 0-based, so step_idx >= consecutive_required - 1
        assert alert_reached_step >= consecutive_required - 1


@given(
    initial_score=st.floats(min_value=0.5, max_value=0.74, allow_nan=False),
    hysteresis_scores=st.lists(
        st.floats(min_value=0.4, max_value=0.49, allow_nan=False),
        min_size=1,
        max_size=30,
    ),
)
def test_hypothesis_hysteresis_holds_above_clear_threshold(
    initial_score: float, hysteresis_scores: List[float]
) -> None:
    """Invariant: State cannot drop back to NORMAL if score stays >= clear_threshold."""
    sm = StateMachine(
        t_suspicious=0.5,
        t_alert=0.75,
        consecutive_alert_count=3,
        clear_threshold=0.4,
    )

    # Ingest initial suspicious score
    sm.update(initial_score)
    assert sm.state == CallState.SUSPICIOUS

    # While scores stay in [0.4, 0.49], state cannot drop to NORMAL
    for score in hysteresis_scores:
        u = sm.update(score)
        assert u.state != CallState.NORMAL


@given(
    scores=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=1,
        max_size=50,
    )
)
def test_hypothesis_alert_emitted_once_per_trigger_cycle(
    scores: List[float],
) -> None:
    """Invariant: alert_triggered fires once per trigger cycle without spam."""
    sm = StateMachine(
        t_suspicious=0.5,
        t_alert=0.75,
        consecutive_alert_count=3,
        clear_threshold=0.4,
    )

    prev_state = CallState.NORMAL
    for score in scores:
        update = sm.update(score)
        if update.alert_triggered:
            # Must be in ALERT
            assert update.state == CallState.ALERT
            # Must be the very first window entering ALERT in this cycle
            assert prev_state != CallState.ALERT
        elif update.state == CallState.ALERT and prev_state == CallState.ALERT:
            # While staying in ALERT, alert_triggered must NOT fire again
            assert not update.alert_triggered

        prev_state = update.state
