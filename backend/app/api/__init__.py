"""API endpoints and WebSocket handlers for VoxGuard."""

from app.api.predict import router as predict_router
from app.api.ws_mic import router as ws_router

__all__ = ["predict_router", "ws_router"]
