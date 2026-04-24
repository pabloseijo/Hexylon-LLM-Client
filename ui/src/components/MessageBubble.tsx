import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../types";
import { useTypewriter } from "../hooks/useTypewriter";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const { role, content, ts, plotFile } = message;

  const date = ts instanceof Date ? ts : new Date(ts);

  const time = date.toLocaleTimeString("es-ES", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const roleLabel =
    role === "user" ? "USUARIO" : role === "assistant" ? "HEXYLON" : "SISTEMA";

  const animatedContent = useTypewriter(role === "assistant" ? content : "");

  if (role === "system") {
    return (
      <div className="animate-fade-up flex w-full px-6">
        <div className="mx-auto w-full max-w-[1080px] flex flex-col items-center">
          
          {/* Header */}
          <div className="mb-1 flex items-center justify-center gap-2">
            <span className="text-[9px] font-semibold tracking-[0.14em] text-[var(--color-warning)]">
              {roleLabel}
            </span>
            <span className="text-[9px] text-[var(--color-text-muted)]">
              {time}
            </span>
          </div>

          {/* Bubble centrada */}
          <div className="max-w-[70%] whitespace-pre-wrap break-words rounded-[var(--radius-md)] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-4 py-2 text-center text-[13px] text-[var(--color-text-strong)]">
            {content}
          </div>

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
              {animatedContent}
            </ReactMarkdown>

            {plotFile && (
              <div className="flex w-full">
                <div className="mx-auto w-full max-w-[1080px]">
                  <div className="mt-3 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-card)] p-3">
                    <img
                      src={`http://127.0.0.1:8001/download?file=${encodeURIComponent(plotFile)}`}
                      alt="Gráfica de la tarea"
                      className="w-full rounded-[var(--radius-sm)]"
                    />

                    <div className="mt-2 text-[11px] text-[var(--color-text-muted)]">
                      Gráfica generada a partir del CSV de la tarea
                    </div>
                  </div>
                </div>
              </div>
            )}

            {!plotFile && role === "assistant" && content.includes("## Resumen") && (
              <div className="flex w-full">
                <div className="mx-auto w-full max-w-[1080px]">
                  <div className="mt-3 text-[11px] text-[var(--color-text-muted)]">
                    No se ha podido generar la gráfica para esta medición.
                  </div>
                </div>
              </div>
            )}
          </div>

        </div>

      </div>
    );
  }

  return (
    <div className="animate-fade-up flex w-full px-6">
      <div className="mx-auto w-full max-w-[1080px] flex flex-col items-end gap-1.5">
        
        {/* Header */}
        <div className="flex flex-row-reverse items-center gap-2">
          <span className="text-[9px] font-semibold tracking-[0.14em] text-[var(--color-accent)]">
            {roleLabel}
          </span>

          <span className="text-[9px] text-[var(--color-text-muted)]">
            {time}
          </span>
        </div>

        {/* Bubble */}
        <div className="max-w-[70%] whitespace-pre-wrap break-words rounded-[var(--radius-md)] rounded-br-[2px] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-4 py-3 text-[13px] leading-relaxed text-[var(--color-text-strong)]">
          {content}
        </div>

      </div>
    </div>
  );
}