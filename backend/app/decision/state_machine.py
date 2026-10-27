"""Hysteresis state machine and decision logic for deepfake call monitoring."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.config import Settings, settings


class CallState(str, Enum):
    """Call safety state categories."""

    NORMAL = "NORMAL"
    SUSPICIOUS = "SUSPICIOUS"
    ALERT = "ALERT"


@dataclass(frozen=True)
class StateUpdate:
    """State transition result emitted for each processed window score."""

    state: CallState
    smoothed_score: float
    alert_triggered: bool
    consecutive_alerts: int


class StateMachine:
    """Three-state machine tracking real-time deepfake risk with hysteresis.

    Transitions:
    - NORMAL -> SUSPICIOUS: when smoothed_score >= t_suspicious
    - NORMAL / SUSPICIOUS -> ALERT: when smoothed_score >= t_alert for
      consecutive_alert_count consecutive windows
    - SUSPICIOUS / ALERT -> NORMAL: strictly when smoothed_score < clear_threshold
    """

    def __init__(
        self,
        config: Optional[Settings] = None,
        t_suspicious: Optional[float] = None,
        t_alert: Optional[float] = None,
        consecutive_alert_count: Optional[int] = None,
        clear_threshold: Optional[float] = None,
    ) -> None:
        cfg = config or settings
        self.t_suspicious: float = (
            t_suspicious if t_suspicious is not None else cfg.t_suspicious
        )
        self.t_alert: float = t_alert if t_alert is not None else cfg.t_alert
        self.consecutive_alert_count: int = (
            consecutive_alert_count
            if consecutive_alert_count is not None
            else cfg.alert_consecutive
        )
        self.clear_threshold: float = (
            clear_threshold if clear_threshold is not None else cfg.clear_threshold
        )

        self._validate_thresholds()

        self._state: CallState = CallState.NORMAL
        self._consecutive_alerts: int = 0
        self._alert_emitted: bool = False
        self._session_alert_emitted: bool = False

    def _validate_thresholds(self) -> None:
        if not (0.0 <= self.clear_threshold < self.t_suspicious < self.t_alert <= 1.0):
            raise ValueError(
                f"Invalid threshold ordering: 0 <= clear ({self.clear_threshold}) "
                f"< suspicious ({self.t_suspicious}) < alert ({self.t_alert}) <= 1.0"
            )
        if self.consecutive_alert_count < 1:
            raise ValueError("consecutive_alert_count must be at least 1")

    @property
    def state(self) -> CallState:
        """Current state of the call session."""
        return self._state

    @property
    def consecutive_alerts(self) -> int:
        """Number of consecutive windows meeting or exceeding t_alert."""
        return self._consecutive_alerts

    @property
    def alert_emitted(self) -> bool:
        """Whether an alert has been emitted in the active trigger cycle."""
        return self._alert_emitted

    @property
    def session_alert_emitted(self) -> bool:
        """Whether an alert has been emitted at any time during this call session."""
        return self._session_alert_emitted

    def update(self, smoothed_score: float) -> StateUpdate:
        """Process a smoothed confidence score and evaluate state transitions."""
        score = float(smoothed_score)

        # Track consecutive alert-level scores
        if score >= self.t_alert:
            self._consecutive_alerts += 1
        else:
            self._consecutive_alerts = 0

        prev_state = self._state

        if self._state == CallState.NORMAL:
            if self._consecutive_alerts >= self.consecutive_alert_count:
                self._state = CallState.ALERT
            elif score >= self.t_suspicious:
                self._state = CallState.SUSPICIOUS
            else:
                self._state = CallState.NORMAL

        elif self._state == CallState.SUSPICIOUS:
            if self._consecutive_alerts >= self.consecutive_alert_count:
                self._state = CallState.ALERT
            elif score < self.clear_threshold:
                self._state = CallState.NORMAL
            else:
                self._state = CallState.SUSPICIOUS

        elif self._state == CallState.ALERT:
            if score < self.clear_threshold:
                self._state = CallState.NORMAL
            else:
                self._state = CallState.ALERT

        # Evaluate alert trigger events
        alert_triggered = False
        if self._state == CallState.ALERT and not self._alert_emitted:
            self._alert_emitted = True
            self._session_alert_emitted = True
            alert_triggered = True

        # When returning to NORMAL, reset the active trigger cycle
        if self._state == CallState.NORMAL and prev_state != CallState.NORMAL:
            self._alert_emitted = False

        return StateUpdate(
            state=self._state,
            smoothed_score=score,
            alert_triggered=alert_triggered,
            consecutive_alerts=self._consecutive_alerts,
        )

    def reset(self) -> None:
        """Reset the state machine to its initial state."""
        self._state = CallState.NORMAL
        self._consecutive_alerts = 0
        self._alert_emitted = False
        self._session_alert_emitted = False


DecisionEngine = StateMachine
