"""Puerta de entrada Open Responses (subconjunto textual documentado).

Soporta JSON, historial explícito, continuidad previous_response_id en un único
proceso y SSE compatible (emisión diferida, no token-by-token).
"""
import hmac
import json
import logging
import os
import time
import uuid
from collections import OrderedDict
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from . import agent

app = FastAPI(title="Banorte CV Agent", version="0.1.0", docs_url="/docs")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("cv-agent")
MODEL_NAME = "cv-agent-v1"
SESSION_TTL = 1800
SESSION_MAX = 300
# Almacenamiento de desarrollo; para replicas múltiples reemplazar por Redis.
_sessions: OrderedDict[str, tuple[float, list[dict[str, str]]]] = OrderedDict()


class ResponsesRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str | None = MODEL_NAME
    input: str | list[dict[str, Any]] | None = None
    stream: bool = False
    previous_response_id: str | None = None
    max_output_tokens: int | None = Field(default=None, ge=1, le=4096)
    store: bool = True
    metadata: dict[str, str] | None = None


async def check_auth(authorization: str | None = Header(None)) -> None:
    expected = os.environ.get("AGENT_API_KEY", "")
    if expected and not hmac.compare_digest(authorization or "", f"Bearer {expected}"):
        raise HTTPException(401, detail="Credenciales inválidas", headers={"WWW-Authenticate": "Bearer"})


def parse_input(value: str | list[dict[str, Any]] | None) -> list[dict[str, str]]:
    if isinstance(value, str):
        return [{"role": "user", "content": value}]
    if value is None:
        return []
    parsed = []
    for item in value[-20:]:
        if item.get("type", "message") != "message":
            continue
        role = item.get("role")
        # Evitar que mensajes arbitrarios conviertan instrucciones del usuario en sistema.
        if role not in {"user", "assistant"}:
            continue
        raw = item.get("content", "")
        if isinstance(raw, str):
            text = raw
        elif isinstance(raw, list):
            text = "\n".join(
                part.get("text", "")
                for part in raw
                if isinstance(part, dict) and part.get("type") in {"input_text", "output_text", "text"}
                and isinstance(part.get("text"), str)
            )
        else:
            continue
        if text.strip():
            parsed.append({"role": role, "content": text[:12000]})
    return parsed


def _session_cleanup() -> None:
    now = time.monotonic()
    for key in list(_sessions):
        if now - _sessions[key][0] > SESSION_TTL:
            _sessions.pop(key, None)
    while len(_sessions) > SESSION_MAX:
        _sessions.popitem(last=False)


def make_response(response_id: str, output_text: str, prev_id: str | None, usage: dict | None,
                  metadata: dict[str, str] | None, sources: list[str], store: bool = True) -> dict:
    now = int(time.time())
    in_tokens = (usage or {}).get("input_tokens", 0)
    out_tokens = (usage or {}).get("output_tokens", 0)
    message = {
        "id": "msg_" + uuid.uuid4().hex,
        "type": "message", "role": "assistant", "status": "completed",
        "content": [{"type": "output_text", "text": output_text, "annotations": []}]
    }
    return {
        "id": response_id, "object": "response", "created_at": now,
        "completed_at": now, "status": "completed", "error": None,
        "incomplete_details": None, "model": MODEL_NAME,
        "output": [message], "previous_response_id": prev_id,
        "instructions": None, "tools": [], "tool_choice": "auto", "truncation": "disabled",
        "parallel_tool_calls": False, "max_output_tokens": None,
        "metadata": metadata or {}, "usage": {
            "input_tokens": in_tokens, "output_tokens": out_tokens,
            "total_tokens": in_tokens + out_tokens,
            "input_tokens_details": {"cached_tokens": (usage or {}).get("input_tokens_details", {}).get("cached_tokens", 0)},
            "output_tokens_details": {"reasoning_tokens": (usage or {}).get("output_tokens_details", {}).get("reasoning_tokens", 0)}
        },
        "text": {"format": {"type": "text"}},
        "top_p": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0,
        "top_logprobs": 0, "temperature": 1.0, "reasoning": None,
        "max_tool_calls": None, "background": False, "service_tier": "default",
        "safety_identifier": None, "prompt_cache_key": None,
        "store": store,
    }


def events_for(response: dict):
    """SSE semántico completo, pero se genera DESPUÉS de completar la inferencia."""
    pending = dict(response)
    pending.update(status="in_progress", completed_at=None, output=[], usage=None)
    msg = response["output"][0]
    msg_start = {"id": msg["id"], "type": "message", "role": "assistant", "status": "in_progress", "content": []}
    text = msg["content"][0]["text"]
    part = {"type": "output_text", "text": text, "annotations": []}
    sequence = [
        ("response.created", {"response": dict(pending, status="queued")}),
        ("response.in_progress", {"response": pending}),
        ("response.output_item.added", {"output_index": 0, "item": msg_start}),
        ("response.content_part.added", {"item_id": msg["id"], "output_index": 0,
                                           "content_index": 0, "part": dict(part, text="")}),
        ("response.output_text.delta", {"item_id": msg["id"], "output_index": 0,
                                          "content_index": 0, "delta": text}),
        ("response.output_text.done", {"item_id": msg["id"], "output_index": 0,
                                         "content_index": 0, "text": text}),
        ("response.content_part.done", {"item_id": msg["id"], "output_index": 0,
                                          "content_index": 0, "part": part}),
        ("response.output_item.done", {"output_index": 0, "item": msg}),
        ("response.completed", {"response": response}),
    ]
    for i, (event_type, payload) in enumerate(sequence):
        data = {"type": event_type, "sequence_number": i, **payload}
        yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/responses", dependencies=[Depends(check_auth)])
async def create_response(request: ResponsesRequest):
    started = time.monotonic()
    _session_cleanup()
    messages = parse_input(request.input)
    if request.previous_response_id:
        history = _sessions.get(request.previous_response_id)
        if history is None:
            raise HTTPException(404, detail="previous_response_id no encontrado o expirado")
        messages = history[1] + messages
    if not messages or messages[-1]["role"] != "user":
        raise HTTPException(422, detail="Se requiere una pregunta del usuario")
    try:
        output_text, usage, sources = await agent.generate(messages)
    except Exception as exc:
        # Nunca registrar el contenido del CV, preguntas ni secretos.
        logger.error("Error durante la inferencia: %s", type(exc).__name__)
        raise HTTPException(502, detail="Servicio de inferencia no disponible") from None
    response_id = "resp_" + uuid.uuid4().hex
    response = make_response(response_id, output_text, request.previous_response_id, usage,
                             request.metadata, sources, request.store)
    if request.store or request.previous_response_id:
        _sessions[response_id] = (time.monotonic(), (messages + [{"role": "assistant", "content": output_text}])[-16:])
        _session_cleanup()
    logger.info("response_id=%s latency_ms=%.0f sources=%s", response_id,
                (time.monotonic() - started) * 1000, ",".join(sources))
    if request.stream:
        return StreamingResponse(events_for(response), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    return response
