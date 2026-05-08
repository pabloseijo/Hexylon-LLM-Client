"""
Cliente real del generador de señales R&S SGU100A.

Comunicación via TCP/IP socket en el puerto 5025.
No requiere VISA ni MCP — conexión socket directa según el manual
R&S SGU100A User Manual, capítulo 12.1.2.4 (Socket communication).

Protocolo:
- Comandos terminados en \\n (newline obligatorio según el manual)
- Solo los queries (comandos que terminan en ?) devuelven respuesta
- Los comandos de escritura no devuelven nada — no hacer recv
- Puerto estándar SCPI socket: 5025
"""

from __future__ import annotations

import socket
from datetime import datetime
from pathlib import Path

from llm.knowledge.generator_command_catalog import get_generator_command_info


_LOG_PATH = Path(__file__).parents[3] / "tmp" / "generator.log"
_DEFAULT_TIMEOUT = 5.0
_BUFFER_SIZE = 4096


class GeneratorClientError(Exception):
    """Error al comunicarse con el generador de señales."""


def _write_log(entry: str) -> None:
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOG_PATH, "a") as f:
        f.write(entry + "\n")


def _is_query(command: str) -> bool:
    """Devuelve True si el comando espera respuesta (termina en ?)."""
    return command.strip().endswith("?")


def send_generator_command(
    command: str,
    machine_id: str = "generator",
    host: str | None = None,
    port: int = 5025,
    timeout: float = _DEFAULT_TIMEOUT,
) -> str:
    """
    Envía un comando SCPI al generador R&S SGU100A via socket TCP.

    Parameters
    ----------
    command:
        Comando SCPI a enviar. El \\n se añade automáticamente.
    machine_id:
        ID de la máquina (para el log).
    host:
        IP del generador. Si es None se lee de machines.json.
    port:
        Puerto TCP. Por defecto 5025 (estándar SCPI socket).
    timeout:
        Timeout en segundos para la conexión y recepción.

    Returns
    -------
    str
        Respuesta del generador para queries.
        "OK" para comandos de escritura.

    Raises
    ------
    GeneratorClientError
        Si hay error de conexión, timeout o respuesta inesperada.
    """
    if host is None:
        host = _resolve_host(machine_id)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    cmd_clean = command.strip()
    is_query = _is_query(cmd_clean)

    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            # El manual indica que el newline es obligatorio
            sock.sendall((cmd_clean + "\n").encode("ascii"))

            if is_query:
                # Solo hacer recv para queries — escrituras no devuelven nada
                response = _receive(sock, timeout)
            else:
                response = "OK"

    except socket.timeout:
        error = f"Timeout ({timeout}s) conectando a {host}:{port}"
        _write_log(
            f"[{timestamp}] machine={machine_id} command={cmd_clean!r} "
            f"status=TIMEOUT error={error!r}"
        )
        raise GeneratorClientError(error)

    except OSError as exc:
        error = f"Error de conexión a {host}:{port}: {exc}"
        _write_log(
            f"[{timestamp}] machine={machine_id} command={cmd_clean!r} "
            f"status=ERROR error={error!r}"
        )
        raise GeneratorClientError(error)

    entry = (
        f"[{timestamp}] "
        f"machine={machine_id} "
        f"host={host}:{port} "
        f"command={cmd_clean!r} "
        f"response={response!r} "
        f"status=OK"
    )
    _write_log(entry)
    print(f"[GENERATOR] {entry}")

    return response


def _receive(sock: socket.socket, timeout: float) -> str:
    """
    Lee la respuesta del generador del socket.
    Lee hasta que no hay más datos o se detecta newline.
    """
    sock.settimeout(timeout)
    chunks: list[bytes] = []

    while True:
        try:
            chunk = sock.recv(_BUFFER_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
            # El SGU100A termina la respuesta con newline
            if b"\n" in chunk:
                break
        except socket.timeout:
            break

    return b"".join(chunks).decode("ascii", errors="replace").strip()


def _resolve_host(machine_id: str) -> str:
    """
    Resuelve la IP del generador desde machines.json.
    """
    import json
    from pathlib import Path as P

    path = P(__file__).parents[3] / "config" / "machines.json"
    try:
        data = json.loads(path.read_text())
        entry = data.get(machine_id)
        if entry is None:
            raise GeneratorClientError(
                f"Máquina '{machine_id}' no encontrada en machines.json"
            )
        url = entry["url"] if isinstance(entry, dict) else entry
        if url == "mock":
            raise GeneratorClientError(
                f"La máquina '{machine_id}' está configurada como mock. "
                f"Actualiza la URL en config/machines.json con la IP real del generador."
            )
        # Extraer host de una URL tipo http://IP:puerto/... o IP directa
        host = url.replace("http://", "").replace("https://", "").split(":")[0].split("/")[0]
        return host
    except GeneratorClientError:
        raise
    except Exception as exc:
        raise GeneratorClientError(
            f"Error leyendo machines.json: {exc}"
        ) from exc


def check_connection(
    host: str,
    port: int = 5025,
    timeout: float = 2.0,
) -> bool:
    """
    Comprueba si el generador es accesible en la red.

    Returns
    -------
    bool
        True si la conexión fue exitosa.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False