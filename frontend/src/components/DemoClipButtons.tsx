import React, { useState } from 'react'
import { Play, ShieldCheck, ShieldAlert, Loader2 } from 'lucide-react'

interface DemoClipButtonsProps {
  onDemoResult?: (result: { verdict: string; p_fake: number; duration: number }) => void
}

/**
 * Synthesizes a valid in-memory WAV file Blob as a fallback.
 */
function createSyntheticWavBlob(durationSeconds: number, amplitude: number): Blob {
  const sampleRate = 16000
  const numSamples = Math.floor(durationSeconds * sampleRate)
  const byteRate = sampleRate * 2
  const blockAlign = 2
  const dataSize = numSamples * 2
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  // RIFF header
  view.setUint32(0, 0x52494646, false)
  view.setUint32(4, 36 + dataSize, true)
  view.setUint32(8, 0x57415645, false)
  view.setUint32(12, 0x666d7420, false)
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, byteRate, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, 16, true)
  view.setUint32(36, 0x64617461, false)
  view.setUint32(40, dataSize, true)

  for (let i = 0; i < numSamples; i++) {
    const t = i / sampleRate
    const sample = amplitude * Math.sin(2 * Math.PI * 440 * t)
    const clamped = Math.max(-1.0, Math.min(1.0, sample))
    const int16 = clamped < 0 ? Math.round(clamped * 32768) : Math.round(clamped * 32767)
    view.setInt16(44 + i * 2, int16, true)
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

export const DemoClipButtons: React.FC<DemoClipButtonsProps> = ({ onDemoResult }) => {
  const [activeClip, setActiveClip] = useState<'real' | 'fake' | null>(null)
  const [lastVerdict, setLastVerdict] = useState<{
    name: string
    verdict: string
    p_fake: number
  } | null>(null)

  const runDemoClip = async (type: 'real' | 'fake') => {
    setActiveClip(type)
    setLastVerdict(null)

    let wavBlob: Blob
    const fileName = type === 'real' ? 'real_sample_1.wav' : 'fake_sample_1.wav'
    const staticUrl = `/demo/${type}/${fileName}`

    try {
      // First attempt: fetch generated benchmark WAV from public/demo
      const res = await fetch(staticUrl)
      if (res.ok) {
        wavBlob = await res.blob()
      } else {
        // Fallback: in-memory synthesized WAV
        const amplitude = type === 'real' ? 0.1 : 0.8
        wavBlob = createSyntheticWavBlob(3.0, amplitude)
      }
    } catch {
      const amplitude = type === 'real' ? 0.1 : 0.8
      wavBlob = createSyntheticWavBlob(3.0, amplitude)
    }

    const formData = new FormData()
    formData.append('file', wavBlob, fileName)

    try {
      const response = await fetch('/api/v1/predict', {
        method: 'POST',
        body: formData,
      })

      if (response.ok) {
        const data = await response.json()
        setLastVerdict({
          name: type === 'real' ? 'Sample Real Voice' : 'Sample Cloned Voice',
          verdict: data.verdict,
          p_fake: data.p_fake,
        })
        if (onDemoResult) {
          onDemoResult({
            verdict: data.verdict,
            p_fake: data.p_fake,
            duration: data.duration_seconds,
          })
        }
      }
    } catch {
      // Handled gracefully
    } finally {
      setActiveClip(null)
    }
  }

  return (
    <div className="hud-panel p-5 border-parchment-200/15">
      <div className="flex items-center justify-between text-xs font-mono text-parchment-200/60 pb-2 mb-3 border-b border-parchment-200/10">
        <span className="flex items-center gap-2">
          <Play className="w-3.5 h-3.5 text-parchment-200" />
          // BENCHMARK_DEMO_REPLAY
        </span>
        <span className="text-[10px]">EVAL_V1</span>
      </div>

      <p className="text-xs font-mono text-parchment-200/60 mb-4 leading-relaxed">
        Test detection instantaneously with pre-synthesized audio benchmarks without microphone permissions.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <button
          onClick={() => runDemoClip('real')}
          disabled={activeClip !== null}
          className="flex items-center justify-between px-3.5 py-2.5 rounded bg-emerald-950/30 border border-emerald-600/40 hover:border-emerald-500 hover:bg-emerald-950/50 transition-all font-mono text-xs text-emerald-300 disabled:opacity-50"
        >
          <span className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            Sample Real Voice
          </span>
          {activeClip === 'real' ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
          ) : (
            <span className="text-[10px] text-emerald-400/60">[PLAY]</span>
          )}
        </button>

        <button
          onClick={() => runDemoClip('fake')}
          disabled={activeClip !== null}
          className="flex items-center justify-between px-3.5 py-2.5 rounded bg-crimson-950/30 border border-crimson-600/40 hover:border-crimson-500 hover:bg-crimson-950/50 transition-all font-mono text-xs text-crimson-300 disabled:opacity-50"
        >
          <span className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-crimson-400" />
            Sample Cloned Voice
          </span>
          {activeClip === 'fake' ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-crimson-400" />
          ) : (
            <span className="text-[10px] text-crimson-400/60">[PLAY]</span>
          )}
        </button>
      </div>

      {lastVerdict && (
        <div className="mt-3.5 p-2.5 rounded bg-void-900 border border-parchment-200/20 text-xs font-mono flex items-center justify-between">
          <span className="text-parchment-200/80">{lastVerdict.name}</span>
          <span
            className={`font-bold px-2 py-0.5 rounded text-[11px] ${
              lastVerdict.verdict === 'REAL'
                ? 'bg-emerald-950 text-emerald-400 border border-emerald-600'
                : 'bg-crimson-950 text-crimson-400 border border-crimson-600'
            }`}
          >
            {lastVerdict.verdict} ({(lastVerdict.p_fake * 100).toFixed(0)}%)
          </span>
        </div>
      )}
    </div>
  )
}
