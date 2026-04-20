import { useState, useEffect } from "react";
import Chat from "./components/Chat";
import TaskPanel from "./components/TaskPanel";
import { useWebSocket } from "./hooks/useWebSocket";
import { getActiveTasks } from "./api/client";
import type { TaskSummary } from "./types";

export default function App() {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const { notifications, connected } = useWebSocket("ws://localhost:8001/ws");

  useEffect(() => {
    getActiveTasks().then(setTasks).catch(() => {});
  }, []);

  useEffect(() => {
    if (!notifications.length) return;

    const last = notifications[notifications.length - 1];
    if (["task_completed", "task_cancelled", "task_failed"].includes(last.type)) {
      setTasks((prev) => prev.filter((t) => t.task_id !== last.task_id));
    }
  }, [notifications]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[var(--color-bg)] text-[var(--color-text)]">
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-panel)] px-5">
        <div className="flex items-center gap-2.5">
          <span className="rounded bg-[var(--color-accent)] px-1.5 py-0.5 text-[13px] font-bold tracking-[0.05em] text-[var(--color-text-inverse)]">
            HX
          </span>

          <div className="flex items-baseline gap-1">
            <span className="font-heading text-[13px] font-semibold tracking-[0.14em] text-[var(--color-text-strong)]">
              HEXYLON
            </span>
            <span className="text-[12px] font-normal tracking-[0.08em] text-[var(--color-text-muted)]">
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
            setTasks((prev) => prev.filter((t) => t.task_id !== id))
          }
        />
      </main>
    </div>
  );
}