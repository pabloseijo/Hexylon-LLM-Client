import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "../types";
import { useTypewriter } from "../hooks/useTypewriter";
import MessageChart from "./MessageChart";

interface Props {
  message: Message;
}

export default function MessageBubble({ message }: Props) {
  const { role, content, ts, plotFile, chartData } = message;

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
        <div className="mx-auto flex w-full max-w-[1080px] flex-col items-center">
          <div className="mb-1 flex items-center justify-center gap-2">
            <span className="text-[9px] font-semibold tracking-[0.14em] text-[var(--color-warning)]">
              {roleLabel}
            </span>
            <span className="text-[9px] text-[var(--color-text-muted)]">
              {time}
            </span>
          </div>

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
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-semibold tracking-[0.14em] text-[var(--color-primary)]">
              {roleLabel}
            </span>

            <span className="text-[9px] text-[var(--color-text-muted)]">
              {time}
            </span>
          </div>

          <div className="markdown-answer break-words text-[13px] leading-relaxed text-[var(--color-text)]">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {animatedContent}
            </ReactMarkdown>

            {chartData?.charts?.map((chart) => (
              <MessageChart key={chart.metric} chartData={chart} />
            ))}

            {!chartData?.charts?.length && plotFile && (
              <div className="mt-4 overflow-hidden rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-card)] p-3">
                <img
                  src={`http://127.0.0.1:8001/download?file=${encodeURIComponent(plotFile)}`}
                  alt="Gráfica de la tarea"
                  className="block max-h-[420px] w-full rounded-[var(--radius-sm)] object-contain"
                />

                <div className="mt-2 text-[11px] text-[var(--color-text-muted)]">
                  Gráfica generada a partir del CSV de la tarea.
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
      <div className="mx-auto flex w-full max-w-[1080px] flex-col items-end gap-1.5">
        <div className="flex flex-row-reverse items-center gap-2">
          <span className="text-[9px] font-semibold tracking-[0.14em] text-[var(--color-accent)]">
            {roleLabel}
          </span>

          <span className="text-[9px] text-[var(--color-text-muted)]">
            {time}
          </span>
        </div>

        <div className="max-w-[70%] whitespace-pre-wrap break-words rounded-[var(--radius-md)] rounded-br-[2px] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-4 py-3 text-[13px] leading-relaxed text-[var(--color-text-strong)]">
          {content}
        </div>
      </div>
    </div>
  );
}