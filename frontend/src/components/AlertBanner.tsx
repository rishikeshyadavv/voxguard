import React from 'react'
import { AlertTriangle, X } from 'lucide-react'

interface AlertBannerProps {
  active: boolean
  onDismiss: () => void
  score: number
  time: number | null
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ active, onDismiss, score, time }) => {
  if (!active) return null

  return (
    <div className="relative w-full overflow-hidden bg-crimson-950/80 border-y-2 border-crimson-600 px-6 py-4 shadow-[0_0_30px_rgba(220,38,38,0.35)] backdrop-blur-md animate-pulse-fast">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="p-2 bg-crimson-600 text-white rounded shadow-lg animate-bounce">
            <AlertTriangle className="w-6 h-6 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold tracking-widest text-crimson-400 uppercase">
                [CRITICAL SECURITY ALERT]
              </span>
              <span className="text-[10px] bg-crimson-900 text-crimson-200 px-1.5 py-0.5 rounded font-mono border border-crimson-700">
                P_SMOOTH: {(score * 100).toFixed(1)}%
              </span>
            </div>
            <p className="text-sm font-semibold text-parchment-100 tracking-wide mt-0.5">
              High confidence synthetic speech signature detected. Possible deepfake impersonation in progress.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {time !== null && (
            <span className="hidden sm:inline text-xs font-mono text-parchment-200/60">
              TIME: {time.toFixed(1)}s
            </span>
          )}
          <button
            onClick={onDismiss}
            className="p-1.5 rounded bg-crimson-900/60 hover:bg-crimson-800 text-parchment-200 hover:text-white transition-colors border border-crimson-700/60"
            title="Dismiss Alert"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
