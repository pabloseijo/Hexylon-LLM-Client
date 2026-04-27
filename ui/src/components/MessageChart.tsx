import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import type { SingleChartData } from "../types";

interface Props {
  chartData: SingleChartData;
}

export default function MessageChart({ chartData }: Props) {
  if (!chartData.points.length) return null;

  return (
    <div className="mt-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-card)] p-4">
      <div className="mb-3">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[var(--color-text-muted)]">
          GRÁFICA INTERACTIVA
        </div>

        <div className="mt-1 text-[13px] font-semibold text-[var(--color-text-strong)]">
          {chartData.metric}
          {chartData.unit ? ` (${chartData.unit})` : ""}
        </div>
      </div>

      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData.points}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="x" tick={{ fontSize: 10 }} minTickGap={24} />
            <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="y"
              name={chartData.y_label}
              stroke="var(--color-accent)"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 text-[11px] text-[var(--color-text-muted)]">
        Datos generados a partir del CSV de la tarea.
      </div>
    </div>
  );
}