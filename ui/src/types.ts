export type MessageRole = "user" | "assistant" | "system";

export interface Message {
  role: MessageRole;
  content: string;
  ts: Date;
}

export interface TaskSummary {
  task_id: string;
  description: string;
  commands: string[];
  interval_seconds: number;
  duration_seconds: number;
  output_file: string;
}

export interface WsNotification {
  type: "task_completed" | "task_cancelled" | "task_failed" | "task_alert";
  task_id: string;
  data: Record<string, string | number | null>;
}

export interface ChatResponse {
  response: string;
}

export interface CancelResponse {
  cancelled: boolean;
  task_id: string;
  message: string;
}