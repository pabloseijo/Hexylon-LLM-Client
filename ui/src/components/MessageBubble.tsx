import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../types";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const { role, content, ts } = message;

  const date = ts instanceof Date ? ts : new Date(ts);

  const time = date.toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const roleLabel =
    role === "user" ? "USUARIO" : role === "assistant" ? "HEXYLON" : "SISTEMA";

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

        <div className="mx-auto whitespace-pre-wrap rounded-[var(--radius-md)] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-4 py-2 text-center text-[16px] text-[var(--color-text-strong)]">
          {content}
        </div>
      </div>
    );
  }

  if (role === "assistant") {
    return (
      <div className="animate-fade-up flex w-full flex-col gap-1.5 px-6">
        
        <div className="mx-auto w-full max-w-[1080px]">

          {/* HEADER */}
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-semibold tracking-[0.14em] text-[var(--color-primary)]">
              {roleLabel}
            </span>

            <span className="text-[9px] text-[var(--color-text-muted)]">
              {time}
            </span>
          </div>

          {/* CONTENIDO */}
          <div className="markdown-answer break-words text-[13px] leading-relaxed text-[var(--color-text)]">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>

        </div>

      </div>
    );
  }

  return (
    <div className="animate-fade-up flex w-full flex-col items-end gap-1.5 px-4">
      <div className="flex flex-row-reverse items-center gap-2">
        <span className="text-[9px] font-semibold tracking-[0.14em] text-[var(--color-accent)]">
          {roleLabel}
        </span>

        <span className="text-[9px] text-[var(--color-text-muted)]">
          {time}
        </span>
      </div>

      <div className="whitespace-pre-wrap break-words rounded-[var(--radius-md)] rounded-br-[2px] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-4 py-3 text-[13px] leading-relaxed text-[var(--color-text-strong)]">
        {content}
      </div>
    </div>
  );
}