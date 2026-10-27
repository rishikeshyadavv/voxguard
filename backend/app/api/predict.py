"""Audio file prediction API endpoint."""

from typing import List

import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.audio.io import load_audio_file
from app.audio.windowing import Windower
from app.config import settings
from app.inference.factory import get_inference_engine

router = APIRouter(prefix="/api/v1", tags=["prediction"])

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB cap
SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg"}


class WindowScore(BaseModel):
    """Deepfake score for a single 2.0 s analysis window."""

    t: float
    p_fake: float


class PredictResponse(BaseModel):
    """File upload evaluation verdict and telemetry response."""

    verdict: str
    p_fake: float
    windows: List[WindowScore]
    duration_seconds: float


@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate audio file for deepfake voice detection",
)
async def predict_audio_file(file: UploadFile = File(...)) -> PredictResponse:
    """Ingest an uploaded audio file and return authenticity verdict and scores."""
    filename = (file.filename or "").lower()
    if not any(filename.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file format for '{file.filename}'. "
                f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            ),
        )

    # Read uploaded bytes with size validation
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file is empty",
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Audio file exceeds the maximum allowed limit of 10 MB",
        )

    # Decode and resample audio
    try:
        audio = load_audio_file(content, target_sr=settings.sample_rate)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to decode audio file payload: {exc}",
        ) from exc

    duration_seconds = len(audio) / settings.sample_rate
    min_required_seconds = settings.window_duration_seconds
    if duration_seconds < min_required_seconds:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Audio duration ({duration_seconds:.2f} s) is shorter than the "
                f"minimum required analysis window ({min_required_seconds:.1f} s)"
            ),
        )

    # Windowing and inference
    windower = Windower(
        window_duration_seconds=settings.window_duration_seconds,
        hop_duration_seconds=settings.hop_duration_seconds,
        sample_rate=settings.sample_rate,
    )
    windows = windower.add_chunk(audio)

    engine = get_inference_engine()
    window_scores: List[WindowScore] = []
    raw_scores: List[float] = []

    for i, window in enumerate(windows):
        p_fake = float(engine.predict(window))
        raw_scores.append(p_fake)
        # Window timestamp represents window end time
        t_sec = round(
            settings.window_duration_seconds + i * settings.hop_duration_seconds, 2
        )
        window_scores.append(WindowScore(t=t_sec, p_fake=round(p_fake, 3)))

    mean_p_fake = float(np.mean(raw_scores)) if raw_scores else 0.0
    verdict = "FAKE" if mean_p_fake >= 0.5 else "REAL"

    return PredictResponse(
        verdict=verdict,
        p_fake=round(mean_p_fake, 3),
        windows=window_scores,
        duration_seconds=round(duration_seconds, 2),
    )
