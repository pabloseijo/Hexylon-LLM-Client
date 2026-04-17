"""
Historial conversacional para el cliente LLM de Hexylon.

Mantiene el historial completo de mensajes del chat actual en el formato
que espera Ollama ({role, content}), y lo pasa en cada llamada al LLM
para que el modelo tenga contexto de toda la conversación.

Diseño:
- Mantiene máximo MAX_TURNS pares usuario/asistente para controlar el tamaño
- Thread-safe mediante Lock
- No persiste entre reinicios (es memoria de sesión)

Uso intencionado:
- Se usa en respuestas narrativas: análisis, sesión, knowledge, how_to
- NO se usa en generate_scpi() para evitar contaminación del output SCPI
"""

from __future__ import annotations

from threading import Lock


class ConversationHistory:
    """
    Historial de mensajes del chat actual.

    Mantiene los mensajes en formato Ollama:
    [
        {"role": "user",      "content": "..."},
        {"role": "assistant", "content": "..."},
        ...
    ]

    Parameters
    ----------
    max_turns:
        Número máximo de pares usuario/asistente a mantener.
        Cuando se supera, se eliminan los más antiguos.
        Por defecto 20 (40 mensajes totales).
    """

    def __init__(self, max_turns: int = 20) -> None:
        self._max_turns = max_turns
        self._messages: list[dict[str, str]] = []
        self._lock = Lock()

    def add_user_message(self, content: str) -> None:
        """Añade un mensaje del usuario al historial."""
        with self._lock:
            self._messages.append({"role": "user", "content": content})
            self._trim()

    def add_assistant_message(self, content: str) -> None:
        """Añade una respuesta del asistente al historial."""
        with self._lock:
            self._messages.append({"role": "assistant", "content": content})
            self._trim()

    def get_messages(self) -> list[dict[str, str]]:
        """Devuelve una copia del historial completo."""
        with self._lock:
            return list(self._messages)

    def build_messages(
        self,
        system_prompt: str,
        extra_user_content: str | None = None,
    ) -> list[dict[str, str]]:
        """
        Construye la lista de mensajes lista para enviar al LLM.

        Incluye el system prompt, el historial completo y opcionalmente
        un mensaje de usuario extra (para inyectar contexto adicional
        como el análisis del CSV o el resumen de sesión).

        Parameters
        ----------
        system_prompt:
            Prompt de sistema que define el rol del LLM.
        extra_user_content:
            Si se proporciona, se añade como mensaje de usuario adicional
            ANTES del último mensaje del usuario del historial. Útil para
            inyectar contexto como el resumen de sesión o el análisis del CSV.

        Returns
        -------
        list[dict[str, str]]
            Lista de mensajes en formato Ollama.
        """
        with self._lock:
            messages = [{"role": "system", "content": system_prompt}]

            if extra_user_content:
                # Historial sin el último mensaje (que ya incluye el contexto)
                history = list(self._messages)
                if history and history[-1]["role"] == "user":
                    # Inyectar contexto antes del último mensaje del usuario
                    messages.extend(history[:-1])
                    messages.append({
                        "role": "user",
                        "content": f"{extra_user_content}\n\n{history[-1]['content']}",
                    })
                else:
                    messages.extend(history)
            else:
                messages.extend(self._messages)

            return messages

    def _trim(self) -> None:
        """
        Elimina los mensajes más antiguos si se supera el límite.
        Siempre elimina pares completos (user + assistant) para mantener
        coherencia en el historial.
        """
        max_messages = self._max_turns * 2
        if len(self._messages) > max_messages:
            # Eliminar desde el principio en pares
            excess = len(self._messages) - max_messages
            # Asegurar que eliminamos un número par para mantener consistencia
            if excess % 2 != 0:
                excess += 1
            self._messages = self._messages[excess:]

    def clear(self) -> None:
        """Limpia el historial completo."""
        with self._lock:
            self._messages.clear()

    @property
    def turn_count(self) -> int:
        """Número de turnos completos (pares user/assistant) en el historial."""
        with self._lock:
            return len(self._messages) // 2

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return len(self._messages) == 0


# Instancia global
conversation_history = ConversationHistory(max_turns=20)