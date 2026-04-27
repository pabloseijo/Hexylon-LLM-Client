"""
Servidor FastAPI para el cliente LLM de Hexylon.

Expone el pipeline como API REST + WebSocket para que el frontend React
pueda consumirlo.

Endpoints:
    POST /chat              → envía un mensaje al pipeline y devuelve respuesta
    GET  /tasks             → lista las tareas activas
    GET  /tasks/history     → historial persistente de tareas
    DELETE /tasks/history   → elimina el historial persistente de tareas
    DELETE /tasks/{task_id} → cancela una tarea activa
    WS   /ws                → WebSocket para notificaciones en tiempo real
    GET  /download          → descarga de CSV generado por tareas

Arrancar:
    PYTHONPATH=src uvicorn src.api.server:app --reload --port 8001
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.task_presenter import task_executor_to_api, task_history_entry_to_api
from api.task_notifier import set_notify_fn
from llm.core.pipeline import run_pipeline
from llm.memory.task_history import task_history
from llm.tasks.task_executor import cancel_task, get_active_tasks

logger = logging.getLogger(__name__)


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
        logger.info(
            "WebSocket conectado. Conexiones activas: %s",
            len(self._connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
            logger.info(
                "WebSocket desconectado. Conexiones activas: %s",
                len(self._connections),
            )

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Envía un mensaje a todas las conexiones activas."""
        dead: list[WebSocket] = []

        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception:
                logger.exception(
                    "Fallo enviando mensaje WS. Se eliminará la conexión."
                )
                dead.append(connection)

        for connection in dead:
            self.disconnect(connection)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Cola de notificaciones de tareas
# ---------------------------------------------------------------------------

_notification_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
_main_loop: asyncio.AbstractEventLoop | None = None


def notify_task_event(event: dict[str, Any]) -> None:
    """
    Encola una notificación desde cualquier hilo.

    Esta función está pensada para ser llamada desde los hilos del executor,
    por lo que debe publicar en el event loop principal mediante
    call_soon_threadsafe.
    """
    if _main_loop is None:
        logger.warning(
            "Loop principal no inicializado. Evento descartado: %s",
            event,
        )
        return

    try:
        logger.info("Encolando evento: %s", event)
        _main_loop.call_soon_threadsafe(_notification_queue.put_nowait, event)
    except Exception:
        logger.exception("No se pudo encolar el evento: %s", event)


async def _notification_dispatcher() -> None:
    """Despacha eventos de la cola al gestor WebSocket."""
    while True:
        event = await _notification_queue.get()
        logger.info("Broadcast evento WS: %s", event)
        await manager.broadcast(event)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop

    _main_loop = asyncio.get_running_loop()
    set_notify_fn(notify_task_event)

    dispatcher_task = asyncio.create_task(_notification_dispatcher())

    try:
        yield
    finally:
        dispatcher_task.cancel()
        try:
            await dispatcher_task
        except asyncio.CancelledError:
            pass


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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Modelos de request/response
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


class TaskSummary(BaseModel):
    task_id: str
    description: str
    commands: list[str]
    interval_seconds: float
    duration_seconds: float
    output_file: str | None = None
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    measurements: int | None = None
    error: str | None = None
    stop_reason: str | None = None


class ChatResponse(BaseModel):
    message: str
    task: TaskSummary | None = None
    plot_file: str | None = None
    chart_data: dict[str, Any] | None = None


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
    El pipeline es síncrono, por lo que se ejecuta en un thread pool.
    """
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, run_pipeline, request.message)

    if isinstance(result, dict):
        task_data = result.get("task")
        task = TaskSummary(**task_data) if task_data else None

        return ChatResponse(
            message=result.get("message", ""),
            task=task,
            plot_file=result.get("plot_file"),
            chart_data=result.get("chart_data"),
        )

    return ChatResponse(message=str(result))

@app.get("/tasks", response_model=list[TaskSummary])
async def list_active_tasks() -> list[TaskSummary]:
    """Lista las tareas activas en este momento."""
    active = get_active_tasks()
    return [
        TaskSummary(**task_executor_to_api(task_id, executor))
        for task_id, executor in active.items()
    ]


@app.get("/tasks/history", response_model=list[TaskSummary])
async def get_task_history(n: int = 20) -> list[TaskSummary]:
    """Devuelve el historial persistente de tareas."""
    return [
        TaskSummary(**task_history_entry_to_api(entry))
        for entry in task_history.get_last(n)
    ]


@app.delete("/tasks/history")
async def clear_task_history() -> dict[str, int | str]:
    """Elimina completamente el historial persistente de tareas."""
    before = len(task_history.get_all())
    task_history.clear()
    after = len(task_history.get_all())

    logger.info("Historial borrado. Antes: %s | Después: %s", before, after)

    return {
        "message": "Historial de tareas eliminado",
        "before": before,
        "after": after,
    }


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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


# ---------------------------------------------------------------------------
# Descarga de ficheros generados por tareas
# ---------------------------------------------------------------------------

@app.get("/download")
def download(file: str = Query(...)) -> FileResponse:
    """
    Descarga un fichero generado por una tarea.

    Valida la ruta recibida y comprueba su existencia real.
    """
    path = Path(file).expanduser().resolve()

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Fichero no encontrado")

    return FileResponse(path, filename=path.name)