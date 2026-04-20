import { useState, useRef, useEffect, KeyboardEvent } from "react";
import MessageBubble from "./MessageBubble";
import { sendMessage } from "../api/client";
import type { Message, WsNotification } from "../types";

interface Props {
  notifications: WsNotification[];
}

const SYSTEM_MESSAGES: Record<string, (n: WsNotification) => string> = {
  task_completed: (n) =>
    `✓ Tarea ${n.task_id} completada — ${n.data?.measurements ?? "?"} mediciones. CSV: ${n.data?.output_file ?? "—"}`,
  task_cancelled: (n) => `✗ Tarea ${n.task_id} cancelada.`,
  task_failed: (n) =>
    `Error en la tarea ${n.task_id}: ${n.data?.error ?? "error desconocido"}`,
  task_alert: (n) => `Alerta en ${n.task_id}: ${n.data?.message ?? ""}`,
};

export default function Chat({ notifications }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Sistema Hexylon LLM activo. Puedes ejecutar comandos, lanzar tareas de medición o realizar consultas sobre la API.",
      ts: new Date(),
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!notifications.length) return;

    const last = notifications[notifications.length - 1];
    const builder = SYSTEM_MESSAGES[last.type];

    if (builder) {
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: builder(last),
          ts: new Date(),
        },
      ]);
    }
  }, [notifications]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text, ts: new Date() },
    ]);

    setLoading(true);

    try {
      const response = await sendMessage(text);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response, ts: new Date() },
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error desconocido";
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: `Error de conexión: ${msg}`,
          ts: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-bg)]">
      <div className="flex h-9 shrink-0 items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-panel)] px-4">
        <span className="text-[10px] font-semibold tracking-[0.14em] text-[var(--color-text-muted)]">
          CONSOLA
        </span>
        <span className="text-[10px] text-[var(--color-text-muted)]">
          {messages.length} mensajes
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="flex min-h-full flex-col gap-4 px-6 py-5">
          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}

          {loading && (
            <div className="self-start rounded-[var(--radius-md)] bg-[var(--color-card)] px-3 py-2">
              <div className="flex gap-1.5">
                <span className="h-1.5 w-1.5 animate-blink rounded-full bg-[var(--color-accent)]" />
                <span className="h-1.5 w-1.5 animate-blink-2 rounded-full bg-[var(--color-accent)]" />
                <span className="h-1.5 w-1.5 animate-blink-3 rounded-full bg-[var(--color-accent)]" />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="flex shrink-0 items-end gap-2 border-t border-[var(--color-border)] bg-[var(--color-panel)] px-4 py-3">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Escribe un comando o una consulta..."
          rows={1}
          disabled={loading}
          className="max-h-28 flex-1 resize-none rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-card)] px-3 py-2 text-[13px] leading-relaxed text-[var(--color-text)] outline-none transition-colors placeholder:text-[var(--color-text-muted)] focus:border-[var(--color-accent)] disabled:opacity-50"
        />

        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="flex h-[34px] w-[34px] shrink-0 cursor-pointer items-center justify-center rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-card)] text-[var(--color-text-muted)] transition-colors hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-soft)] hover:text-[var(--color-accent)] disabled:cursor-not-allowed disabled:opacity-30"
          aria-label="Enviar mensaje"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path
              d="M2 8L14 2L8 14L7 9L2 8Z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinejoin="round"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}