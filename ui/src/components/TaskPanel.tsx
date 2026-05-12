import { useState } from "react";
import { cancelTask } from "../api/client";
import type { TaskSummary, WsNotification } from "../types";
import type { AnyProgress, SweepProgress } from "../App";

interface TaskCardProps {
  task: TaskSummary;
  onCancelled: (id: string) => void;
  progress?: AnyProgress;
}

function isSweepProgress(p: AnyProgress): p is SweepProgress {
  return "current_freq_mhz" in p;
}

function TaskCard({ task, onCancelled, progress }: TaskCardProps) {
  const [cancelling, setCancelling] = useState(false);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await cancelTask(task.task_id);
      onCancelled(task.task_id);
    } catch {
      setCancelling(false);
    }
  };

  const status = task.status ?? "active";

  const statusConfig = {
    active: { label: "ACTIVA", color: "var(--color-primary)", bg: "var(--color-primary-soft)" },
    completed: { label: "FINALIZADA", color: "var(--color-success)", bg: "rgba(46,125,50,0.1)" },
    failed: { label: "ERROR", color: "var(--color-danger)", bg: "rgba(198,40,40,0.1)" },
    cancelled: { label: "CANCELADA", color: "var(--color-warning)", bg: "rgba(246,164,0,0.1)" },
  };

  const cfg = statusConfig[status as keyof typeof statusConfig] || statusConfig.active;

  return (
    <div className="animate-slide-in flex flex-col gap-2 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-card)] p-3">

      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] text-[var(--color-text-muted)]">
          {task.task_id.replace("task_", "")}
        </span>
        <span
          className="rounded px-1.5 py-0.5 text-[9px] font-semibold tracking-[0.14em]"
          style={{ color: cfg.color, background: cfg.bg }}
        >
          {cfg.label}
        </span>
      </div>

      {/* Descripción */}
      <p className="text-xs leading-snug text-[var(--color-text)]">
        {task.description}
      </p>

      {/* Datos */}
      <div className="flex items-start justify-between gap-3 text-[10px] text-[var(--color-text-muted)]">
        <span className="min-w-0 break-words">
          {task.commands?.join(", ") || "—"}
        </span>
        <span className="shrink-0">
          {task.interval_seconds}s / {task.duration_seconds}s
        </span>
      </div>

      {/* Barra de progreso */}
      {progress && status === "active" && (
        <div className="flex flex-col gap-1">
          <div className="flex justify-between text-[9px] text-[var(--color-text-muted)]">
            {isSweepProgress(progress) ? (
              <span>{progress.current_freq_mhz.toFixed(0)} MHz</span>
            ) : (
              <span>{progress.elapsed_seconds.toFixed(0)}s transcurridos</span>
            )}
            <span>{progress.current_step} / {progress.total_steps} · {progress.percent}%</span>
          </div>
          <div className="h-1 w-full overflow-hidden rounded-full bg-[var(--color-border)]">
            <div
              className="h-full rounded-full bg-[var(--color-accent)] transition-all duration-300"
              style={{ width: `${progress.percent}%` }}
            />
          </div>
        </div>
      )}

      {/* CSV */}
      {task.output_file && (
        <a
          href={`http://127.0.0.1:8001/download?file=${encodeURIComponent(task.output_file ?? "")}`}
          target="_blank"
          rel="noreferrer"
          className="text-[10px] text-[var(--color-accent)] underline"
        >
          Descargar CSV
        </a>
      )}

      {/* Cancelar */}
      {status === "active" && (
        <button
          onClick={handleCancel}
          disabled={cancelling}
          className="mt-1 self-end rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-card)] px-2 py-1 text-[10px] text-[var(--color-text-muted)] transition-colors hover:border-[var(--color-danger)] hover:bg-[rgba(198,40,40,0.06)] hover:text-[var(--color-danger)] disabled:cursor-not-allowed disabled:opacity-40 cursor-pointer"
        >
          {cancelling ? "Cancelando..." : "Cancelar"}
        </button>
      )}
    </div>
  );
}

interface Props {
  tasks: TaskSummary[];
  notifications: WsNotification[];
  taskProgress: Record<string, AnyProgress>;
  onTaskCancelled: (id: string) => void;
  onClearHistory: () => void;
}

export default function TaskPanel({
  tasks,
  notifications,
  taskProgress,
  onTaskCancelled,
  onClearHistory,
}: Props) {
  const alerts = notifications.filter((n) => n.type === "task_alert");

  function getTaskTime(task: TaskSummary): number {
    const raw = task.started_at ?? task.finished_at ?? task.task_id.replace("task_", "").replace("_", "");
    const parsed = Date.parse(raw);
    if (!Number.isNaN(parsed)) return parsed;
    const match = task.task_id.match(/task_(\d{8})_(\d{6})/);
    if (match) {
      const [, date, time] = match;
      return Date.parse(
        `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}T${time.slice(0, 2)}:${time.slice(2, 4)}:${time.slice(4, 6)}`
      );
    }
    return 0;
  }

  const sortByNewest = (a: TaskSummary, b: TaskSummary) => getTaskTime(b) - getTaskTime(a);
  const activeTasks = tasks.filter((t) => t.status === "active").sort(sortByNewest);
  const finishedTasks = tasks.filter((t) => t.status !== "active").sort(sortByNewest);

  return (
    <aside className="flex w-[280px] shrink-0 flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-panel)]">

      {/* Header */}
      <div className="flex h-9 shrink-0 items-center justify-between border-b border-[var(--color-border)] px-4">
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-semibold tracking-[0.14em] text-[var(--color-text-muted)]">
            TAREAS
          </span>
          <button
            onClick={onClearHistory}
            className="text-[9px] font-semibold tracking-[0.1em] text-[var(--color-danger)] transition-opacity hover:opacity-80 cursor-pointer border border-[var(--color-border)] bg-[var(--color-card)] px-2 py-1 disabled:cursor-not-allowed disabled:opacity-40"
          >
            LIMPIAR HISTÓRICO
          </button>
        </div>
        <span className="rounded bg-[var(--color-accent-soft)] px-1.5 py-0.5 text-[11px] font-semibold text-[var(--color-accent)]">
          {activeTasks.length}
        </span>
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-3">

        {/* ACTIVAS */}
        {activeTasks.length === 0 ? (
          <p className="py-4 text-center text-[11px] text-[var(--color-text-muted)]">
            Sin tareas activas
          </p>
        ) : (
          activeTasks.map((t) => (
            <TaskCard
              key={t.task_id}
              task={t}
              onCancelled={onTaskCancelled}
              progress={taskProgress[t.task_id]}
            />
          ))
        )}

        {/* HISTÓRICO */}
        {finishedTasks.length > 0 && (
          <>
            <div className="mt-2 border-t border-[var(--color-border)] pt-3">
              <div className="pb-1 text-[9px] font-semibold tracking-[0.14em] text-[var(--color-text-muted)]">
                HISTÓRICO
              </div>
            </div>
            {finishedTasks.map((t) => (
              <TaskCard
                key={t.task_id}
                task={t}
                onCancelled={onTaskCancelled}
              />
            ))}
          </>
        )}

        {/* ALERTAS */}
        {alerts.length > 0 && (
          <>
            <div className="mt-2 border-t border-[var(--color-border)] pt-3">
              <div className="pb-1 text-[9px] font-semibold tracking-[0.14em] text-[var(--color-text-muted)]">
                ALERTAS
              </div>
            </div>
            {alerts.slice(-5).map((a, i) => (
              <div
                key={i}
                className="flex items-start gap-2 rounded-[var(--radius-lg)] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-2.5 py-2 text-[11px] text-[var(--color-text-strong)]"
              >
                <span className="shrink-0 text-[var(--color-warning)]">⚠</span>
                <span>{String(a.data?.message ?? "")}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </aside>
  );
}