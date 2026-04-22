import type { ChatResponse, CancelResponse, TaskSummary } from "../types";

const BASE = "http://127.0.0.1:8001";

export async function sendMessage(message: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function getActiveTasks(): Promise<TaskSummary[]> {
  const res = await fetch(`${BASE}/tasks`);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function getTaskHistory(n = 20): Promise<TaskSummary[]> {
  const res = await fetch(`${BASE}/tasks/history?n=${n}`);

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function cancelTask(taskId: string): Promise<CancelResponse> {
  const res = await fetch(`${BASE}/tasks/${taskId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return res.json();
}

export async function clearTaskHistory(): Promise<void> {
  const res = await fetch(`${BASE}/tasks/history`, {
    method: "DELETE",
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
}