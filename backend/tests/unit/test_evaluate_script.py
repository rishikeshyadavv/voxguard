"""Unit tests for evaluation metrics computation."""

from scripts.evaluate import compute_metrics


def test_compute_metrics_perfect_accuracy() -> None:
    results = [
        {
            "file": "real1.wav",
            "true_label": "REAL",
            "mean_p_fake": 0.1,
            "alert_triggered": False,
            "is_correct": True,
        },
        {
            "file": "real2.wav",
            "true_label": "REAL",
            "mean_p_fake": 0.15,
            "alert_triggered": False,
            "is_correct": True,
        },
        {
            "file": "fake1.wav",
            "true_label": "FAKE",
            "mean_p_fake": 0.85,
            "alert_triggered": True,
            "is_correct": True,
        },
        {
            "file": "fake2.wav",
            "true_label": "FAKE",
            "mean_p_fake": 0.9,
            "alert_triggered": True,
            "is_correct": True,
        },
    ]

    metrics = compute_metrics(results)
    assert metrics["accuracy"] == 100.0
    assert metrics["mean_real_score"] == 0.125
    assert metrics["mean_fake_score"] == 0.875
    assert metrics["far"] == 0.0
    assert metrics["frr"] == 0.0
    assert metrics["eer"] == 0.0


def test_compute_metrics_with_false_alarms_and_misses() -> None:
    results = [
        # Real clip false alarm
        {
            "file": "real_noisy.wav",
            "true_label": "REAL",
            "mean_p_fake": 0.8,
            "alert_triggered": True,
            "is_correct": False,
        },
        # Real clip correct
        {
            "file": "real_clean.wav",
            "true_label": "REAL",
            "mean_p_fake": 0.1,
            "alert_triggered": False,
            "is_correct": True,
        },
        # Fake clip missed
        {
            "file": "fake_subtle.wav",
            "true_label": "FAKE",
            "mean_p_fake": 0.3,
            "alert_triggered": False,
            "is_correct": False,
        },
        # Fake clip detected
        {
            "file": "fake_obvious.wav",
            "true_label": "FAKE",
            "mean_p_fake": 0.95,
            "alert_triggered": True,
            "is_correct": True,
        },
    ]

    metrics = compute_metrics(results)
    assert metrics["accuracy"] == 50.0  # 2 of 4 correct
    assert metrics["far"] == 50.0  # 1 of 2 reals triggered alert
    assert metrics["frr"] == 50.0  # 1 of 2 fakes missed
