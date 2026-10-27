import React from 'react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import { TelemetryPoint } from '../hooks/useVoxSocket'

interface ScoreChartProps {
  data: TelemetryPoint[]
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: number
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-void-900 border border-parchment-200/20 p-2.5 rounded shadow-xl text-xs font-mono">
        <div className="text-parchment-200/60 mb-1 border-b border-parchment-200/10 pb-0.5">
          TIME: {label !== undefined ? `${label.toFixed(1)}s` : '--'}
        </div>
        {payload.map((entry) => (
          <div key={entry.name} className="flex items-center justify-between gap-4 py-0.5">
            <span style={{ color: entry.color }} className="font-medium">
              {entry.name}:
            </span>
            <span className="text-parchment-200 font-bold">
              {typeof entry.value === 'number' ? entry.value.toFixed(3) : entry.value}
            </span>
          </div>
        ))}
      </div>
    )
  }
  return null
}

export const ScoreChart: React.FC<ScoreChartProps> = ({ data }) => {
  const chartData = data.length > 0 ? data : [{ t: 0, p_fake: 0, p_smooth: 0, state: 'NORMAL' }]

  return (
    <div className="hud-panel p-5 flex flex-col h-full border-parchment-200/15">
      <div className="flex items-center justify-between mb-3 text-xs font-mono text-parchment-200/60 pb-2 border-b border-parchment-200/10">
        <span className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-crimson-500 rounded-full animate-pulse" />
          // REAL-TIME_TELEMETRY_STREAM (p_smooth vs p_fake)
        </span>
        <div className="flex items-center gap-4 text-[10px]">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-amber-400 inline-block" />
            p_smooth
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-0.5 bg-crimson-500 inline-block" />
            p_fake (raw)
          </span>
        </div>
      </div>

      <div className="w-full h-64 sm:h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#22222a" />
            <XAxis
              dataKey="t"
              stroke="#6b7280"
              fontSize={10}
              tickFormatter={(v) => `${Number(v).toFixed(1)}s`}
            />
            <YAxis
              domain={[0, 1]}
              stroke="#6b7280"
              fontSize={10}
              ticks={[0, 0.25, 0.5, 0.75, 1.0]}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip content={<CustomTooltip />} />

            {/* Threshold References */}
            <ReferenceLine
              y={0.75}
              stroke="#dc2626"
              strokeDasharray="4 4"
              label={{
                value: 'ALERT (0.75)',
                position: 'insideTopRight',
                fill: '#ef4444',
                fontSize: 9,
                fontFamily: 'monospace',
              }}
            />
            <ReferenceLine
              y={0.5}
              stroke="#d97706"
              strokeDasharray="4 4"
              label={{
                value: 'SUSPICIOUS (0.50)',
                position: 'insideTopRight',
                fill: '#f59e0b',
                fontSize: 9,
                fontFamily: 'monospace',
              }}
            />

            {/* Raw window prediction line */}
            <Line
              type="monotone"
              dataKey="p_fake"
              name="p_fake"
              stroke="#ef4444"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />

            {/* Smoothed confidence curve */}
            <Line
              type="monotone"
              dataKey="p_smooth"
              name="p_smooth"
              stroke="#f59e0b"
              strokeWidth={2.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
