import os
from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.predict import router as predict_router
from app.api.ws_mic import router as ws_router
from app.config import settings

app = FastAPI(
    title="VoxGuard API",
    description="Real-time voice deepfake detection API",
    version="0.1.0",
)

origins = [
    origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
]
if not origins:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router)
app.include_router(ws_router)

# Mount benchmark demo clips if directory is present
demo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "demo"))
if os.path.isdir(demo_dir):
    app.mount("/demo", StaticFiles(directory=demo_dir), name="demo")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "model_version": "stub"}
