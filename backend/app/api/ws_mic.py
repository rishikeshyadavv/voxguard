"""WebSocket endpoint for real-time microphone stream analysis."""

import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.audio.buffer import RingBuffer
from app.audio.io import decode_pcm16
from app.audio.windowing import Windower
from app.config import settings
from app.decision.smoothing import ScoreSmoother
from app.decision.state_machine import StateMachine
from app.inference.factory import get_inference_engine

router = APIRouter(tags=["streaming"])
logger = logging.getLogger("voxguard.ws_mic")


@router.websocket("/ws/mic")
async def websocket_mic_endpoint(websocket: WebSocket) -> None:
    """Accept PCM16 audio frames from browser microphone and stream live verdicts."""
    await websocket.accept()

    ring_buffer = RingBuffer(
        capacity_seconds=30.0,
        sample_rate=settings.sample_rate,
    )
    windower = Windower(
        window_duration_seconds=settings.window_duration_seconds,
        hop_duration_seconds=settings.hop_duration_seconds,
        sample_rate=settings.sample_rate,
    )
    smoother = ScoreSmoother(window_size=settings.smooth_n)
    state_machine = StateMachine()
    engine = get_inference_engine()

    total_windows_processed = 0

    try:
        while True:
            message = await websocket.receive()
            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                break

            # Handle text metadata frame (e.g. sample rate configuration handshake)
            if "text" in message and message["text"] is not None:
                text_data = message["text"]
                try:
                    meta: Dict[str, Any] = json.loads(text_data)
                    req_sr = meta.get("sample_rate")
                    if req_sr is not None and int(req_sr) != settings.sample_rate:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": (
                                    f"Unsupported sample rate: {req_sr} Hz. "
                                    f"VoxGuard expects {settings.sample_rate} Hz."
                                ),
                            }
                        )
                except Exception as exc:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Malformed JSON message: {exc}",
                        }
                    )
                continue

            # Handle binary PCM16 audio chunks
            if "bytes" in message and message["bytes"] is not None:
                pcm_bytes: bytes = message["bytes"]
                if len(pcm_bytes) == 0:
                    continue

                try:
                    samples = decode_pcm16(pcm_bytes)
                except Exception as exc:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"PCM decode error: {exc}",
                        }
                    )
                    continue

                ring_buffer.append(samples)

                for window in windower.process(samples):
                    total_windows_processed += 1
                    t_sec = round(
                        settings.window_duration_seconds
                        + (total_windows_processed - 1) * settings.hop_duration_seconds,
                        2,
                    )

                    try:
                        p_fake = float(engine.predict(window))
                    except Exception as exc:
                        logger.error("Inference execution error: %s", exc)
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": f"Inference error: {exc}",
                            }
                        )
                        continue

                    p_smooth = float(smoother.append(p_fake))
                    state_update = state_machine.update(p_smooth)

                    score_payload = {
                        "type": "score",
                        "t": t_sec,
                        "p_fake": round(p_fake, 3),
                        "p_smooth": round(p_smooth, 3),
                        "state": state_update.state.value,
                    }
                    await websocket.send_json(score_payload)

                    if state_update.alert_triggered:
                        alert_payload = {
                            "type": "alert",
                            "t": t_sec,
                            "p_smooth": round(p_smooth, 3),
                        }
                        await websocket.send_json(alert_payload)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally from /ws/mic")
    except Exception as exc:
        logger.warning("WebSocket session terminated with exception: %s", exc)
    finally:
        ring_buffer.clear()
        windower.clear()
        smoother.clear()
        state_machine.reset()
