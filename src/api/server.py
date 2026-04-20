"""
Servidor FastAPI para el cliente LLM de Hexylon.

Expone el pipeline como API REST + WebSocket para que el frontend React
pueda consumirlo.

Endpoints:
    POST /chat              →  envía un mensaje al pipeline y devuelve respuesta
    GET  /tasks             →  lista las tareas activas
    DELETE /tasks/{task_id} →  cancela una tarea activa
    GET  /tasks/history     →  historial persistente de tareas
    WS   /ws                →  WebSocket para notificaciones en tiempo real

Arrancar:
    PYTHONPATH=src uvicorn src.api.server:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm.core.pipeline import run_pipeline
from llm.memory.task_history import task_history
from llm.tasks.task_executor import cancel_task, get_active_tasks


# ---------------------------------------------------------------------------
# Gestor de conexiones WebSocket
# ---------------------------------------------------------------------------

class ConnectionManager:
    """Gestiona las conexiones WebSocket activas."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Envía un mensaje a todas las conexiones activas."""
        dead: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Cola de notificaciones de tareas
# ---------------------------------------------------------------------------

# Cola asyncio para pasar notificaciones desde hilos de tareas al loop asyncio
_notification_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()


def notify_task_event(event: dict[str, Any]) -> None:
    """
    Llamado desde hilos de tareas (síncronos) para encolar una notificación.
    Se ejecuta desde el thread del executor, no desde el loop asyncio.
    """
    try:
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(_notification_queue.put_nowait, event)
    except Exception:
        pass


async def _notification_dispatcher() -> None:
    """
    Tarea asyncio que lee la cola y hace broadcast a los WebSocket.
    Corre en background mientras el servidor está activo.
    """
    while True:
        event = await _notification_queue.get()
        await manager.broadcast(event)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranca el dispatcher de notificaciones al iniciar el servidor."""
    task = asyncio.create_task(_notification_dispatcher())
    yield
    task.cancel()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Hexylon LLM API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringir al dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Modelos de request/response
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


class TaskSummary(BaseModel):
    task_id: str
    description: str
    commands: list[str]
    interval_seconds: float
    duration_seconds: float
    output_file: str


class CancelResponse(BaseModel):
    cancelled: bool
    task_id: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints REST
# ---------------------------------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Envía un mensaje al pipeline y devuelve la respuesta.
    El pipeline es síncrono — se ejecuta en un thread para no bloquear.
    """
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, run_pipeline, request.message)
    return ChatResponse(response=response)


@app.get("/tasks", response_model=list[TaskSummary])
async def list_active_tasks() -> list[TaskSummary]:
    """Lista las tareas activas en este momento."""
    active = get_active_tasks()
    return [
        TaskSummary(
            task_id=task_id,
            description=executor.plan.description,
            commands=executor.plan.commands,
            interval_seconds=executor.plan.interval_seconds,
            duration_seconds=executor.plan.duration_seconds,
            output_file=executor.plan.output_file,
        )
        for task_id, executor in active.items()
    ]


@app.delete("/tasks/{task_id}", response_model=CancelResponse)
async def cancel_active_task(task_id: str) -> CancelResponse:
    """Cancela una tarea activa por su ID."""
    cancelled = cancel_task(task_id)
    if cancelled:
        return CancelResponse(
            cancelled=True,
            task_id=task_id,
            message=f"Tarea {task_id} cancelada.",
        )
    return CancelResponse(
        cancelled=False,
        task_id=task_id,
        message=f"No se encontró la tarea {task_id} o ya finalizó.",
    )


@app.get("/tasks/history")
async def get_task_history(n: int = 20) -> list[dict[str, Any]]:
    """Devuelve el historial persistente de tareas."""
    return task_history.get_last(n)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Conexión WebSocket para notificaciones en tiempo real.

    El frontend se conecta aquí y recibe eventos cuando:
    - una tarea se completa
    - una tarea es cancelada
    - una tarea falla
    - una alerta es disparada

    Formato de mensaje:
    {
        "type": "task_completed" | "task_cancelled" | "task_failed" | "task_alert",
        "task_id": "...",
        "data": { ... }
    }
    """
    await manager.connect(websocket)
    try:
        while True:
            # Mantener la conexión viva esperando mensajes del cliente
            # (el cliente puede enviar pings o mensajes de keepalive)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)