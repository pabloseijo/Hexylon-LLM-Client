import { useState } from "react";
import { cancelTask } from "../api/client";
import type { TaskSummary, WsNotification } from "../types";

interface TaskCardProps {
  task: TaskSummary;
  onCancelled: (id: string) => void;
}

function TaskCard({ task, onCancelled }: TaskCardProps) {
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

  return (
    <div className="animate-slide-in flex flex-col gap-2 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-card)] p-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] text-[var(--color-text-muted)]">
          {task.task_id.replace("task_", "")}
        </span>

        <span className="rounded bg-[var(--color-primary-soft)] px-1.5 py-0.5 text-[9px] font-semibold tracking-[0.14em] text-[var(--color-primary)]">
          ACTIVA
        </span>
      </div>

      <p className="text-xs leading-snug text-[var(--color-text)]">
        {task.description}
      </p>

      <div className="flex items-start justify-between gap-3 text-[10px] text-[var(--color-text-muted)]">
        <span className="min-w-0 break-words">{task.commands.join(", ")}</span>
        <span className="shrink-0">
          {task.interval_seconds}s / {task.duration_seconds}s
        </span>
      </div>

      <button
        onClick={handleCancel}
        disabled={cancelling}
        className="mt-1 self-end rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-card)] px-2 py-1 text-[10px] text-[var(--color-text-muted)] transition-colors hover:border-[var(--color-danger)] hover:bg-[color:rgba(198,40,40,0.06)] hover:text-[var(--color-danger)] disabled:cursor-not-allowed disabled:opacity-40"
      >
        {cancelling ? "Cancelando..." : "Cancelar"}
      </button>
    </div>
  );
}

interface Props {
  tasks: TaskSummary[];
  notifications: WsNotification[];
  onTaskCancelled: (id: string) => void;
}

export default function TaskPanel({
  tasks,
  notifications,
  onTaskCancelled,
}: Props) {
  const alerts = notifications.filter((n) => n.type === "task_alert");

  return (
    <aside className="flex w-[280px] shrink-0 flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-panel)]">
      <div className="flex h-9 shrink-0 items-center justify-between border-b border-[var(--color-border)] px-4">
        <span className="text-[10px] font-semibold tracking-[0.14em] text-[var(--color-text-muted)]">
          TAREAS
        </span>

        <span className="rounded bg-[var(--color-accent-soft)] px-1.5 py-0.5 text-[11px] font-semibold text-[var(--color-accent)]">
          {tasks.length}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-3">
        {tasks.length === 0 ? (
          <p className="py-6 text-center text-[11px] text-[var(--color-text-muted)]">
            Sin tareas activas
          </p>
        ) : (
          tasks.map((t) => (
            <TaskCard
              key={t.task_id}
              task={t}
              onCancelled={onTaskCancelled}
            />
          ))
        )}

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
                className="flex items-start gap-2 rounded-[var(--radius-md)] border border-[var(--color-accent)] bg-[var(--color-accent-soft)] px-2.5 py-2 text-[11px] text-[var(--color-text-strong)]"
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