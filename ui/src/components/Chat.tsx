import { useState, useRef, useEffect } from "react";
import type { KeyboardEvent } from "react";
import MessageBubble from "./MessageBubble";
import { sendMessage } from "../api/client";
import type { Message, WsNotification } from "../types";

interface Props {
  notifications: WsNotification[];
}

const SYSTEM_MESSAGES: Record<string, (n: WsNotification) => string> = {
  task_completed: (n) =>
    `✓ Tarea ${n.task_id} completada — ${n.data?.measurements ?? "?"} mediciones`,
  task_cancelled: (n) => `✗ Tarea ${n.task_id} cancelada`,
  task_failed: (n) =>
    `Error en tarea ${n.task_id}: ${n.data?.error ?? "error desconocido"}`,
  task_alert: (n) =>
    `Alerta en ${n.task_id}: ${n.data?.message ?? ""}`,
};

function getResponseMessage(response: unknown): string {
  if (typeof response === "string") return response;

  if (
    typeof response === "object" &&
    response !== null &&
    "message" in response &&
    typeof (response as { message?: unknown }).message === "string"
  ) {
    return (response as { message: string }).message;
  }

  return String(response);
}

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
  const abortRef = useRef<AbortController | null>(null);

  const hasText = input.trim().length > 0;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!notifications.length) return;

    const last = notifications[notifications.length - 1];
    const builder = SYSTEM_MESSAGES[last.type];

    if (!builder) return;

    queueMicrotask(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: "system",
          content: builder(last),
          ts: new Date(),
        },
      ]);
    });
  }, [notifications]);

  const resizeInput = () => {
    const textarea = inputRef.current;
    if (!textarea) return;

    textarea.style.height = "auto";

    const maxHeight = 160;
    const nextHeight = Math.min(textarea.scrollHeight, maxHeight);

    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY =
      textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  };

  useEffect(() => {
    resizeInput();
  }, [input]);

  const handleAbort = () => {
    abortRef.current?.abort();
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");

    setMessages((prev) => [
      ...prev,
      { role: "user", content: text, ts: new Date() },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);

    try {
      const response = await sendMessage(text, {
        signal: controller.signal,
      });

      console.log("CHAT_RESPONSE:", response);

      const assistantText = getResponseMessage(response);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: assistantText,
          ts: new Date(),
          plotFile: response.plot_file ?? null,
          chartData: response.chart_data ?? null, // NUEVO
        },
      ]);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setMessages((prev) => [
          ...prev,
          {
            role: "system",
            content: "Generación interrumpida por el usuario.",
            ts: new Date(),
          },
        ]);
      } else {
        const msg = err instanceof Error ? err.message : "Error desconocido";

        setMessages((prev) => [
          ...prev,
          {
            role: "system",
            content: `Error de conexión: ${msg}`,
            ts: new Date(),
          },
        ]);
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
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
            <div className="flex w-full px-6">
              <div className="mx-auto w-full max-w-[1080px]">
                <div className="mt-1">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--color-card)]">
                    <div className="h-5 w-5 animate-breathe rounded-full bg-[var(--color-accent)]" />
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="shrink-0 bg-[var(--color-bg)] px-6 pb-2 pt-3">
        <div className="mx-auto w-full max-w-[1080px]">
          <div className="flex items-end gap-3 rounded-[28px] border border-[var(--color-border)] bg-[var(--color-panel)] px-5 py-4 shadow-[0_6px_24px_rgba(0,0,0,0.06)]">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Escribe un comando o una consulta..."
              rows={1}
              disabled={loading}
              className="
                max-h-40 min-h-[28px] flex-1 resize-none
                overflow-hidden bg-transparent px-0 py-0
                text-[15px] leading-relaxed text-[var(--color-text)]
                outline-none
                placeholder:text-[var(--color-text-muted)]
                disabled:opacity-50
              "
            />

            <button
              type="button"
              onClick={() => {
                if (loading) {
                  handleAbort();
                  return;
                }

                void handleSend();
              }}
              disabled={!loading && !hasText}
              className={`
                flex h-8 w-8 shrink-0 items-center justify-center
                rounded-full
                transition-all duration-200

                ${
                  loading
                    ? "cursor-pointer bg-[var(--color-text-muted)] text-white hover:opacity-90"
                    : hasText
                      ? "cursor-pointer bg-[var(--color-accent)] text-[var(--color-text-inverse)] hover:opacity-90"
                      : "cursor-not-allowed bg-[var(--color-accent)] text-[var(--color-text-inverse)] opacity-35"
                }
              `}
              aria-label={loading ? "Interrumpir generación" : "Enviar mensaje"}
            >
              {loading ? (
                <div className="h-3 w-3 rounded-[2px] bg-white" />
              ) : (
                <svg width="18" height="18" viewBox="0 0 16 16" fill="none">
                  <path
                    d="M2 8L14 2L8 14L7 9L2 8Z"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </button>
          </div>
        </div>

        <div className="mt-2 text-center">
          <p className="text-[11px] text-[var(--color-text-muted)]">
            El sistema puede cometer errores. Verifica siempre la información crítica antes de utilizarla.
          </p>
        </div>
      </div>
    </div>
  );
}