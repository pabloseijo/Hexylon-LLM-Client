import { useCallback, useEffect, useState } from "react";
import Chat from "./components/Chat";
import TaskPanel from "./components/TaskPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import { getActiveTasks } from "./api/client";
import type { TaskStatus, TaskSummary, WsNotification } from "./types";

function upsertTask(
  prev: TaskSummary[],
  incoming: TaskSummary
): TaskSummary[] {
  const exists = prev.some((t) => t.task_id === incoming.task_id);

  if (exists) {
    return prev.map((t) =>
      t.task_id === incoming.task_id ? { ...t, ...incoming } : t
    );
  }

  return [incoming, ...prev];
}

function asTaskSummary(data: Record<string, unknown>): TaskSummary | null {
  if (
    typeof data.task_id !== "string" ||
    typeof data.description !== "string" ||
    !Array.isArray(data.commands) ||
    typeof data.interval_seconds !== "number" ||
    typeof data.duration_seconds !== "number"
  ) {
    return null;
  }

  const commands = data.commands.filter(
    (value): value is string => typeof value === "string"
  );

  return {
    task_id: data.task_id,
    description: data.description,
    commands,
    interval_seconds: data.interval_seconds,
    duration_seconds: data.duration_seconds,
    output_file:
      typeof data.output_file === "string" ? data.output_file : null,
    status: "active",
  };
}

function normalizeStatus(status: TaskStatus | undefined): TaskStatus {
  return status ?? "active";
}

export default function App() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const { notifications, connected } = useWebSocket("ws://127.0.0.1:8001/ws");

  const syncActiveTasks = useCallback(async () => {
    try {
      const activeTasks = await getActiveTasks();

      setTasks((prev) => {
        let next = [...prev];

        for (const task of activeTasks) {
          next = upsertTask(next, {
            ...task,
            output_file: task.output_file ?? null,
            status: "active",
          });
        }

        return next;
      });
    } catch {
      // Sin acción
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void syncActiveTasks();
    });
  }, [syncActiveTasks]);

  useEffect(() => {
    if (!connected) return;

    queueMicrotask(() => {
      void syncActiveTasks();
    });
  }, [connected, syncActiveTasks]);

  useEffect(() => {
    if (!notifications.length) return;

    const last: WsNotification = notifications[notifications.length - 1];

    if (
      ["task_created", "task_started", "task_launched"].includes(last.type) &&
      last.data
    ) {
      const task = asTaskSummary(last.data);
      if (!task) return;

      queueMicrotask(() => {
        setTasks((prev) => upsertTask(prev, task));
      });      
      return;
    }

    if (last.type === "task_completed") {
      setTasks((prev) =>
        prev.map((t) =>
          t.task_id === last.task_id
            ? {
                ...t,
                status: "completed",
                output_file:
                  typeof last.data?.output_file === "string"
                    ? last.data.output_file
                    : (t.output_file ?? null),
              }
            : t
        )
      );
      return;
    }

    if (last.type === "task_failed") {
      setTasks((prev) =>
        prev.map((t) =>
          t.task_id === last.task_id
            ? {
                ...t,
                status: "failed",
                output_file:
                  typeof last.data?.output_file === "string"
                    ? last.data.output_file
                    : (t.output_file ?? null),
              }
            : t
        )
      );
      return;
    }

    if (last.type === "task_cancelled") {
      setTasks((prev) =>
        prev.map((t) =>
          t.task_id === last.task_id
            ? {
                ...t,
                status: "cancelled",
              }
            : t
        )
      );
    }
  }, [notifications]);

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-[var(--color-bg)] text-[var(--color-text)]">
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-panel)] px-5">
        <div className="flex items-center gap-2.5">
          <span className="rounded bg-[var(--color-accent)] px-1.5 py-0.5 text-[13px] font-bold tracking-[0.05em] text-[var(--color-text-inverse)]">
            HX
          </span>

          <div className="flex items-baseline gap-1">
            <span className="font-heading text-[13px] font-semibold tracking-[0.14em] text-[var(--color-text-strong)]">
              HEXYLON
            </span>
            <span className="text-[12px] text-[var(--color-text-muted)]">
              LLM INTERFACE
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              connected ? "animate-pulse-dot" : ""
            }`}
            style={{
              backgroundColor: connected
                ? "var(--color-success)"
                : "var(--color-warning)",
              boxShadow: connected
                ? "0 0 6px var(--color-success)"
                : "0 0 6px var(--color-warning)",
            }}
          />

          <span
            className="text-[10px] font-semibold tracking-[0.14em]"
            style={{
              color: connected
                ? "var(--color-success)"
                : "var(--color-warning)",
            }}
          >
            {connected ? "CONNECTED" : "RECONNECTING"}
          </span>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 gap-4 overflow-hidden bg-[var(--color-bg)] p-4">
        <Chat notifications={notifications} />

        <TaskPanel
          tasks={tasks.map((t) => ({
            ...t,
            status: normalizeStatus(t.status),
          }))}
          notifications={notifications}
          onTaskCancelled={(id) =>
            setTasks((prev) =>
              prev.map((t) =>
                t.task_id === id ? { ...t, status: "cancelled" } : t
              )
            )
          }
        />
      </main>
    </div>
  );
}