import React from 'react'
import { ShieldAlert, ShieldCheck, Shield } from 'lucide-react'
import { CallState } from '../hooks/useVoxSocket'

interface ConfidenceMeterProps {
  score: number // in [0, 1]
  state: CallState
}

export const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({ score, state }) => {
  const percentage = Math.round(score * 100)

  // Meter configuration
  const radius = 68
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (score * circumference)

  const stateColors = {
    NORMAL: {
      stroke: '#10b981', // emerald-500
      glow: 'drop-shadow(0 0 10px rgba(16, 185, 129, 0.4))',
      text: 'text-emerald-400',
      border: 'border-emerald-500/30',
      bg: 'bg-emerald-950/20',
      label: 'NORMAL // VERIFIED',
      icon: ShieldCheck,
    },
    SUSPICIOUS: {
      stroke: '#f59e0b', // amber-500
      glow: 'drop-shadow(0 0 12px rgba(245, 158, 11, 0.5))',
      text: 'text-amber-400',
      border: 'border-amber-500/40',
      bg: 'bg-amber-950/25',
      label: 'SUSPICIOUS // ANOMALY',
      icon: Shield,
    },
    ALERT: {
      stroke: '#ef4444', // crimson-500
      glow: 'drop-shadow(0 0 16px rgba(239, 68, 68, 0.7))',
      text: 'text-crimson-500 text-glow-crimson animate-pulse',
      border: 'border-crimson-600',
      bg: 'bg-crimson-950/30',
      label: 'CRITICAL ALERT // SYNTHETIC',
      icon: ShieldAlert,
    },
  }[state]

  const StateIcon = stateColors.icon

  return (
    <div className={`hud-panel p-6 flex flex-col items-center justify-center ${stateColors.border} transition-colors duration-500`}>
      <div className="w-full flex items-center justify-between text-xs text-parchment-200/50 mb-4 pb-2 border-b border-parchment-200/10 font-mono">
        <span>// CONFIDENCE_GAUGE</span>
        <span>SYS.V1</span>
      </div>

      <div className="relative flex items-center justify-center">
        {/* SVG Circular Meter */}
        <svg className="w-48 h-48 -rotate-90 transform" viewBox="0 0 160 160">
          {/* Background circle track */}
          <circle
            cx="80"
            cy="80"
            r={radius}
            stroke="currentColor"
            strokeWidth="8"
            className="text-void-800"
            fill="transparent"
          />
          {/* Active progress track */}
          <circle
            cx="80"
            cy="80"
            r={radius}
            stroke={stateColors.stroke}
            strokeWidth="8"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
            style={{ filter: stateColors.glow }}
            className="transition-all duration-300 ease-out"
          />
        </svg>

        {/* Center telemetry readout */}
        <div className="absolute flex flex-col items-center justify-center text-center">
          <StateIcon className={`w-6 h-6 mb-1 ${stateColors.text}`} />
          <span className={`text-4xl font-extrabold tracking-tight font-mono ${stateColors.text}`}>
            {percentage}%
          </span>
          <span className="text-[10px] uppercase font-mono tracking-wider text-parchment-200/60 mt-0.5">
            p_fake
          </span>
        </div>
      </div>

      {/* State badge */}
      <div className={`mt-5 px-3 py-1.5 rounded border ${stateColors.border} ${stateColors.bg} flex items-center gap-2`}>
        <span className={`w-2 h-2 rounded-full ${state === 'ALERT' ? 'bg-crimson-500 animate-ping' : state === 'SUSPICIOUS' ? 'bg-amber-400' : 'bg-emerald-400'}`} />
        <span className={`text-xs font-mono font-semibold tracking-wide ${stateColors.text}`}>
          {stateColors.label}
        </span>
      </div>
    </div>
  )
}
