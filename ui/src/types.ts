export type TaskStatus = "active" | "completed" | "failed" | "cancelled";

export interface TaskSummary {
  task_id: string;
  description: string;
  commands: string[];
  interval_seconds: number;
  duration_seconds: number;
  output_file?: string | null;
  status: TaskStatus;
  started_at?: string | null;
  finished_at?: string | null;
  measurements?: number | null;
  error?: string | null;
  stop_reason?: string | null;
}

export interface ChatResponse {
  message: string;
  task?: TaskSummary | null;
  plot_file?: string | null;
  chart_data?: ChartData | null;
}

export interface CancelResponse {
  cancelled: boolean;
  task_id: string;
  message: string;
}

export interface WsNotification {
  type: string;
  task_id: string;
  data?: Record<string, unknown>;
}

export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  ts: Date;
  plotFile?: string | null;
  chartData?: ChartData | null; 
}

export interface ChartPoint {
  x: string;
  y: number;
}

export interface SingleChartData {
  metric: string;
  metric_column?: string;
  unit?: string | null;
  x_label: string;
  y_label: string;
  points: ChartPoint[];
  source_file?: string;
}

export interface ChartData {
  charts: SingleChartData[];
  source_file?: string;
}

export interface WsNotification {
  type: string;
  task_id: string;
  data?: Record<string, unknown>;
}