"""Score smoothing using a moving average over recent inference windows."""

from collections import deque
from typing import Deque, List, Optional

from app.config import settings


class ScoreSmoother:
    """Computes a moving average over the last N prediction scores.

    If fewer than N scores have been ingested, computes the average
    over the currently available window count.
    """

    def __init__(self, window_size: Optional[int] = None) -> None:
        size = window_size if window_size is not None else settings.smooth_n
        if size <= 0:
            raise ValueError("window_size must be positive")

        self.window_size: int = size
        self._history: Deque[float] = deque(maxlen=self.window_size)

    def append(self, score: float) -> float:
        """Append a new raw prediction score and return the current smoothed average."""
        val = float(score)
        self._history.append(val)
        return self.current_score

    @property
    def current_score(self) -> float:
        """Current smoothed score as the mean of recent windows."""
        if not self._history:
            return 0.0
        return float(sum(self._history) / len(self._history))

    @property
    def scores(self) -> List[float]:
        """List copy of the scores currently retained in the window."""
        return list(self._history)

    def __len__(self) -> int:
        """Number of scores currently buffered in the moving average window."""
        return len(self._history)

    def reset(self) -> None:
        """Reset the score smoother, clearing all history."""
        self._history.clear()

    def clear(self) -> None:
        """Alias for reset."""
        self.reset()
