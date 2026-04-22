import { useCallback, useEffect, useState } from "react";
import Chat from "./components/Chat";
import TaskPanel from "./components/TaskPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import {
  clearTaskHistory,
  getActiveTasks,
  getTaskHistory,
} from "./api/client";
import type { TaskSummary, WsNotification } from "./types";

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

function isTaskSummary(data: unknown): data is TaskSummary {
  if (typeof data !== "object" || data === null) return false;

  const value = data as Record<string, unknown>;

  return (
    typeof value.task_id === "string" &&
    typeof value.description === "string" &&
    Array.isArray(value.commands) &&
    typeof value.interval_seconds === "number" &&
    typeof value.duration_seconds === "number" &&
    typeof value.status === "string"
  );
}

export default function App() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const { notifications, connected } = useWebSocket("ws://127.0.0.1:8001/ws");

  const syncTasks = useCallback(async () => {
    try {
      const [activeTasks, historyTasks] = await Promise.all([
        getActiveTasks(),
        getTaskHistory(20),
      ]);

      let next: TaskSummary[] = [];

      for (const task of historyTasks) {
        next = upsertTask(next, task);
      }

      for (const task of activeTasks) {
        next = upsertTask(next, task);
      }

      setTasks(next);
    } catch {
      // sin acción por ahora
    }
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      void syncTasks();
    });
  }, [syncTasks]);

  useEffect(() => {
    if (!connected) return;

    queueMicrotask(() => {
      void syncTasks();
    });
  }, [connected, syncTasks]);

  useEffect(() => {
    if (!notifications.length) return;

    const last: WsNotification = notifications[notifications.length - 1];

    if (
      ["task_created", "task_started", "task_launched"].includes(last.type) &&
      isTaskSummary(last.data)
    ) {
      queueMicrotask(() => {
        setTasks((prev) => upsertTask(prev, last.data));
      });
      return;
    }

    if (
      ["task_completed", "task_failed", "task_cancelled"].includes(last.type) &&
      isTaskSummary(last.data)
    ) {
      queueMicrotask(() => {
        setTasks((prev) => upsertTask(prev, last.data));
      });
    }
  }, [notifications]);

  const handleClearHistory = async () => {
    try {
      await clearTaskHistory();

      // Vaciado inmediato visual
      setTasks([]);

      // Reconstrucción real desde backend
      await syncTasks();
    } catch {
      // sin acción por ahora
    }
  };

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
          tasks={tasks}
          notifications={notifications}
          onTaskCancelled={(id) =>
            setTasks((prev) =>
              prev.map((t) =>
                t.task_id === id ? { ...t, status: "cancelled" } : t
              )
            )
          }
          onClearHistory={handleClearHistory}
        />
      </main>
    </div>
  );
}