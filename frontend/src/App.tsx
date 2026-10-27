import React, { useEffect, useState } from 'react'
import {
  Mic,
  MicOff,
  Radio,
  Activity,
  Layers,
  Terminal,
} from 'lucide-react'
import { useVoxSocket } from './hooks/useVoxSocket'
import { ConfidenceMeter } from './components/ConfidenceMeter'
import { ScoreChart } from './components/ScoreChart'
import { AlertBanner } from './components/AlertBanner'
import { AudioUploader } from './components/AudioUploader'
import { DemoClipButtons } from './components/DemoClipButtons'
import { CentralFissure } from './components/CentralFissure'

export const App: React.FC = () => {
  const {
    connectionStatus,
    isStreaming,
    currentScore,
    history,
    alertActive,
    error,
    startStreaming,
    stopStreaming,
    dismissAlert,
  } = useVoxSocket()

  const [backendHealth, setBackendHealth] = useState<string>('checking...')

  useEffect(() => {
    fetch('/health')
      .then((res) => {
        if (!res.ok) throw new Error('Health probe failed')
        return res.json()
      })
      .then((data) => setBackendHealth(`${data.status} (model: ${data.model_version})`))
      .catch(() => setBackendHealth('offline'))
  }, [])

  return (
    <div className="min-h-screen bg-void-950 text-parchment-200 flex flex-col font-mono bg-tech-grid relative overflow-x-hidden">
      {/* Alert Banner */}
      <AlertBanner
        active={alertActive}
        onDismiss={dismissAlert}
        score={currentScore.p_smooth}
        time={currentScore.t}
      />

      {/* Main HUD Header */}
      <header className="border-b border-parchment-200/15 bg-void-900/90 backdrop-blur-md px-6 py-4 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="p-2.5 bg-void-850 border border-parchment-200/20 rounded text-crimson-500 shadow-[0_0_15px_rgba(220,38,38,0.25)]">
              <Layers className="w-6 h-6 stroke-[2]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-crimson-500 font-bold tracking-wider">01+</span>
                <h1 className="text-xl sm:text-2xl font-extrabold tracking-wider font-display text-parchment-100 uppercase">
                  VoxGuard
                </h1>
                <span className="text-[10px] bg-void-800 text-parchment-200/60 px-1.5 py-0.5 rounded border border-parchment-200/10">
                  PROTO-V0.1
                </span>
              </div>
              <p className="text-xs text-parchment-200/50 tracking-wider">
                REAL-TIME VOICE DEEPFAKE DETECTION &bull; 16 kHz HUD
              </p>
            </div>
          </div>

          {/* Status Badges */}
          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Live State Badge */}
            <div
              className={`px-3 py-1 rounded border text-xs font-semibold tracking-wider flex items-center gap-2 transition-colors ${
                currentScore.state === 'ALERT'
                  ? 'bg-crimson-950/60 border-crimson-600 text-crimson-400 animate-pulse'
                  : currentScore.state === 'SUSPICIOUS'
                  ? 'bg-amber-950/60 border-amber-500 text-amber-400'
                  : 'bg-emerald-950/40 border-emerald-600/60 text-emerald-400'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  currentScore.state === 'ALERT'
                    ? 'bg-crimson-500 animate-ping'
                    : currentScore.state === 'SUSPICIOUS'
                    ? 'bg-amber-400'
                    : 'bg-emerald-400'
                }`}
              />
              STATE: {currentScore.state}
            </div>

            {/* Socket Status */}
            <div className="px-3 py-1 rounded bg-void-850 border border-parchment-200/15 text-xs text-parchment-200/70 flex items-center gap-1.5">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  connectionStatus === 'CONNECTED'
                    ? 'bg-emerald-400'
                    : connectionStatus === 'CONNECTING'
                    ? 'bg-amber-400 animate-ping'
                    : 'bg-void-700'
                }`}
              />
              WS: {connectionStatus}
            </div>

            {/* Backend Health */}
            <div className="hidden md:flex px-3 py-1 rounded bg-void-850 border border-parchment-200/15 text-xs text-parchment-200/60 items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-parchment-200/50" />
              API: {backendHealth}
            </div>
          </div>
        </div>
      </header>

      {/* Main Grid Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 flex flex-col gap-6">
        {/* Error notification if any */}
        {error && (
          <div className="p-3 bg-crimson-950/40 border border-crimson-600/70 rounded text-xs font-mono text-crimson-300 flex items-center justify-between">
            <span>[PIPELINE_ERROR]: {error}</span>
          </div>
        )}

        {/* Flanked Layout with Central Fissure */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Wing: Streaming Telemetry & Confidence Meter (7 cols) */}
          <section className="lg:col-span-7 flex flex-col gap-6">
            {/* Live Stream Control Banner */}
            <div className="hud-panel p-5 border-parchment-200/15">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Radio
                      className={`w-4 h-4 ${
                        isStreaming ? 'text-crimson-500 animate-pulse' : 'text-parchment-200/50'
                      }`}
                    />
                    <h2 className="text-sm font-bold text-parchment-100 uppercase tracking-wider font-display">
                      Microphone AudioWorklet Ingest
                    </h2>
                  </div>
                  <p className="text-xs text-parchment-200/60">
                    Captures 16 kHz little-endian PCM16 chunks via Web Audio and streams live frames.
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  {isStreaming ? (
                    <button
                      onClick={stopStreaming}
                      className="px-5 py-2.5 rounded bg-crimson-600 hover:bg-crimson-700 text-white font-mono text-xs font-bold tracking-wider flex items-center gap-2 shadow-[0_0_15px_rgba(220,38,38,0.4)] transition-all"
                    >
                      <MicOff className="w-4 h-4" />
                      HALT MIC
                    </button>
                  ) : (
                    <button
                      onClick={startStreaming}
                      className="px-5 py-2.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold tracking-wider flex items-center gap-2 shadow-[0_0_15px_rgba(16,185,129,0.3)] transition-all"
                    >
                      <Mic className="w-4 h-4" />
                      STREAM MIC
                    </button>
                  )}
                </div>
              </div>
            </div>

            {/* Confidence Meter & Real-time Score Chart */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-1">
                <ConfidenceMeter score={currentScore.p_smooth} state={currentScore.state} />
              </div>
              <div className="md:col-span-2">
                <ScoreChart data={history} />
              </div>
            </div>
          </section>

          {/* Central Tectonic Fissure Divider (hidden on small screens) */}
          <div className="hidden lg:flex lg:col-span-1 justify-center h-full">
            <CentralFissure />
          </div>

          {/* Right Wing: File Upload & Demo Benchmark Suite (4 cols) */}
          <section className="lg:col-span-4 flex flex-col gap-6">
            <AudioUploader />
            <DemoClipButtons />
          </section>
        </div>
      </main>

      {/* Cyber-Gothic HUD Footer */}
      <footer className="border-t border-parchment-200/10 bg-void-900/60 px-6 py-3 text-[11px] font-mono text-parchment-200/40">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 text-center sm:text-left">
          <div className="flex items-center gap-2">
            <Terminal className="w-3.5 h-3.5 text-parchment-200/40" />
            <span>VOXGUARD // IN-MEMORY RING BUFFER (PRIVACY PRESERVED)</span>
          </div>
          <div>
            <span>WINDOW: 2.0s &bull; HOP: 0.5s &bull; SMOOTH_N: 6 &bull; T_ALERT: 0.75</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
