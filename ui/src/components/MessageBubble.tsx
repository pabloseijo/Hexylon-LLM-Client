import type { Message } from "../types";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const { role, content, ts } = message;

  // =========================
  // Normalización de fecha
  // =========================
  const date = ts instanceof Date ? ts : new Date(ts);

  const time = date.toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const roleLabel =
    role === "user" ? "USUARIO" : role === "assistant" ? "HEXYLON" : "SISTEMA";

  // =========================
  // SISTEMA
  // =========================
  if (role === "system") {
    return (
      <div className="animate-fade-up w-full px-6">
        <div className="mb-1 flex items-center justify-center gap-2">
          <span className="text-[9px] font-semibold tracking-[0.14em] text-[var(--color-warning)]">
            {roleLabel}
          </span>
          <span className="text-[9px] text-[var(--color-text-muted)]">
            {time}
          </span>
        </div>

        <div className="mx-auto max-w-[70%] whitespace-pre-wrap rounded-[var(--radius-md)] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-4 py-2 text-center text-[11px] text-[var(--color-text-strong)]">
          {content}
        </div>
      </div>
    );
  }

  const isUser = role === "user";

  // =========================
  // CONFIGURACIÓN BURBUJA
  // =========================
  const bubbleStyle = isUser
    ? "rounded-[var(--radius-md)] rounded-br-[2px] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-text-strong)]"
    : "rounded-[var(--radius-md)] rounded-bl-[2px] border border-[var(--color-primary)] bg-[var(--color-primary-soft)] text-[var(--color-text)]";

  return (
    <div
      className={`animate-fade-up flex w-full flex-col gap-1.5 px-4 ${
        isUser ? "items-end" : "items-start"
      }`}
    >
      {/* Header */}
      <div
        className={`flex items-center gap-2 ${
          isUser ? "flex-row-reverse" : ""
        }`}
      >
        <span
          className={`text-[9px] font-semibold tracking-[0.14em] ${
            isUser
              ? "text-[var(--color-accent)]"
              : "text-[var(--color-primary)]"
          }`}
        >
          {roleLabel}
        </span>

        <span className="text-[9px] text-[var(--color-text-muted)]">
          {time}
        </span>
      </div>

      {/* Bubble */}
      <div
        className={`max-w-[70%] whitespace-pre-wrap break-words px-4 py-3 text-[13px] leading-relaxed ${bubbleStyle}`}
      >
        {content}
      </div>
    </div>
  );
}