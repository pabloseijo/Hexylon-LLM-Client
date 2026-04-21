export type MessageRole = "user" | "assistant" | "system";
export type TaskStatus = "active" | "completed" | "failed" | "cancelled";
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
  output_file?: string | null;
  status?: TaskStatus;
}

export interface WsNotification {
  type: string;
  task_id: string;
  data?: Record<string, unknown>;
}

export interface ChatResponse {
  message: string;
  task?: TaskSummary | null;
}

export interface CancelResponse {
  cancelled: boolean;
  task_id: string;
  message: string;
}