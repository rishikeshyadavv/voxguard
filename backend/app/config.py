"""Global configuration settings for VoxGuard."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """VoxGuard configuration settings with environment variable fallbacks."""

    # Model backend ("stub", "hf", "onnx")
    model_backend: str = os.getenv("MODEL_BACKEND", "stub")
    hf_model_name: str = os.getenv(
        "HF_MODEL_NAME", "MattyB95/AST-VOXCELEB-SPOOFING-HOTFIX"
    )
    hf_device: str = os.getenv("HF_DEVICE", "cpu")

    # Audio pipeline parameters
    sample_rate: int = int(os.getenv("SAMPLE_RATE", "16000"))
    window_duration_seconds: float = float(os.getenv("WINDOW_DURATION_SECONDS", "2.0"))
    hop_duration_seconds: float = float(os.getenv("HOP_DURATION_SECONDS", "0.5"))

    # Decision logic parameters (docs/PROTOTYPE.md Section 2.3)
    smooth_n: int = int(os.getenv("SMOOTH_N", "6"))
    t_suspicious: float = float(os.getenv("T_SUSPICIOUS", "0.5"))
    t_alert: float = float(os.getenv("T_ALERT", "0.75"))
    alert_consecutive: int = int(os.getenv("ALERT_CONSECUTIVE", "3"))
    clear_threshold: float = float(os.getenv("CLEAR_THRESHOLD", "0.4"))

    # Security & CORS
    cors_origins: str = os.getenv("CORS_ORIGINS", "*")


settings = Settings()
