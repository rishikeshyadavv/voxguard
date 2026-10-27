import { useEffect, useState } from 'react'
import { Shield, Activity, Radio, UploadCloud } from 'lucide-react'

export function App() {
  const [healthStatus, setHealthStatus] = useState<string>('checking...')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => {
        if (!res.ok) {
          throw new Error('Health check failed')
        }
        return res.json()
      })
      .then((data) => setHealthStatus(`${data.status} (model: ${data.model_version})`))
      .catch(() => setHealthStatus('backend offline'))
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20 text-indigo-400">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">VoxGuard</h1>
            <p className="text-xs text-slate-400">Real-time Voice Deepfake Detection</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-slate-800 border border-slate-700 text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Backend: {healthStatus}
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        <section className="md:col-span-2 bg-slate-900/50 border border-slate-800 rounded-xl p-6 flex flex-col items-center justify-center text-center">
          <div className="p-4 bg-slate-800/50 rounded-full mb-4 text-slate-400">
            <Activity className="w-8 h-8" />
          </div>
          <h2 className="text-lg font-semibold mb-2">Live Stream Telemetry</h2>
          <p className="text-sm text-slate-400 max-w-md mb-6">
            Real-time deepfake probability scoring and rolling confidence meter will appear here.
          </p>
          <div className="flex gap-4">
            <button
              disabled
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600/50 text-indigo-200 cursor-not-allowed font-medium text-sm"
            >
              <Radio className="w-4 h-4" /> Start Mic Stream
            </button>
          </div>
        </section>

        <section className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-4 text-slate-200">
              <UploadCloud className="w-5 h-5 text-indigo-400" />
              <h2 className="text-md font-semibold">Audio File Analysis</h2>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Upload wav, mp3, or flac clips to obtain an immediate authenticity verdict.
            </p>
            <div className="border border-dashed border-slate-700 rounded-lg p-6 text-center text-xs text-slate-500">
              Audio dropzone (Step 4 & 5)
            </div>
          </div>
          <div className="mt-6 pt-4 border-t border-slate-800 text-xs text-slate-400 text-center">
            VoxGuard Prototype v0.1.0 &bull; 16 kHz Mono Pipeline
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
