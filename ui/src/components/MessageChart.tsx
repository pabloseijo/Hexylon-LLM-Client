import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { SingleChartData } from "../types";

interface Props {
  chartData: SingleChartData;
}

type ChartRow = {
  x: string | number;
  y?: number;
  [key: string]: string | number | undefined;
};

function isMatrixChart(chartData: SingleChartData): boolean {
  return Array.isArray(chartData.series) && chartData.series.length > 0;
}

function buildMatrixRows(chartData: SingleChartData): ChartRow[] {
  const xValues = new Set<string | number>();

  for (const serie of chartData.series ?? []) {
    for (const point of serie.points) {
      xValues.add(point.x);
    }
  }

  return Array.from(xValues)
    .sort((a, b) => Number(a) - Number(b))
    .map((x) => {
      const row: ChartRow = { x };

      for (const serie of chartData.series ?? []) {
        const point = serie.points.find((p) => p.x === x);
        if (point) {
          row[serie.label] = point.y;
        }
      }

      return row;
    });
}

export default function MessageChart({ chartData }: Props) {
  const matrix = isMatrixChart(chartData);

  const data: ChartRow[] = matrix
    ? buildMatrixRows(chartData)
    : (chartData.points ?? []).map((point) => ({
        x: point.x,
        y: point.y,
      }));

  if (!data.length) return null;

  return (
    <div className="mt-4 rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-card)] p-4">
      <div className="mb-3">
        <div className="text-[10px] font-semibold tracking-[0.14em] text-[var(--color-text-muted)]">
          GRÁFICA INTERACTIVA
        </div>

        <div className="mt-1 text-[13px] font-semibold text-[var(--color-text-strong)]">
          {chartData.machine_id ? `${chartData.machine_id} — ` : ""}
          {chartData.metric}
          {chartData.unit ? ` (${chartData.unit})` : ""}
        </div>
      </div>

      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="x" tick={{ fontSize: 10 }} minTickGap={24} />
            <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
            <Tooltip />
            {matrix && <Legend />}

            {matrix
              ? chartData.series?.map((serie) => (
                  <Line
                    key={serie.label}
                    type="monotone"
                    dataKey={serie.label}
                    name={serie.label}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                    isAnimationActive={false}
                    connectNulls
                  />
                ))
              : (
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
                )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 text-[11px] text-[var(--color-text-muted)]">
        Datos generados a partir del CSV de la tarea.
      </div>
    </div>
  );
}