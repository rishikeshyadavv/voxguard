from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.predict import router as predict_router
from app.api.ws_mic import router as ws_router

app = FastAPI(
    title="VoxGuard API",
    description="Real-time voice deepfake detection API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predict_router)
app.include_router(ws_router)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "model_version": "stub"}
