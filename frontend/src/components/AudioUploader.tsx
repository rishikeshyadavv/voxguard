import React, { useState, useRef } from 'react'
import { UploadCloud, CheckCircle2, AlertOctagon, Loader2, Music } from 'lucide-react'

interface WindowScore {
  t: number
  p_fake: number
}

interface PredictResult {
  verdict: 'REAL' | 'FAKE'
  p_fake: number
  windows: WindowScore[]
  duration_seconds: number
}

export const AudioUploader: React.FC = () => {
  const [isDragging, setIsDragging] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<PredictResult | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  const processFile = async (file: File) => {
    setErrorMessage(null)
    setResult(null)
    setFileName(file.name)
    setIsLoading(true)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/v1/predict', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Analysis failed' }))
        throw new Error(errorData.detail || `Server returned ${response.status}`)
      }

      const data: PredictResult = await response.json()
      setResult(data)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = () => {
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0])
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0])
    }
  }

  return (
    <div className="hud-panel p-5 border-parchment-200/15 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between text-xs font-mono text-parchment-200/60 pb-2 mb-4 border-b border-parchment-200/10">
          <span className="flex items-center gap-2">
            <UploadCloud className="w-4 h-4 text-parchment-200" />
            // FILE_ANALYSIS_DROPZONE
          </span>
          <span className="text-[10px]">CAP: 10MB</span>
        </div>

        {/* Drop area */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all duration-200 ${
            isDragging
              ? 'border-crimson-500 bg-crimson-950/20'
              : 'border-parchment-200/20 hover:border-parchment-200/40 bg-void-900/60'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".wav,.mp3,.flac,.ogg"
            className="hidden"
            onChange={handleFileChange}
          />
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-2">
              <Loader2 className="w-8 h-8 text-amber-400 animate-spin mb-2" />
              <span className="text-xs font-mono text-amber-300">Processing Audio Spectrum...</span>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-2">
              <Music className="w-8 h-8 text-parchment-200/40 mb-2" />
              <span className="text-xs font-mono text-parchment-200 font-semibold mb-1">
                Drop audio clip or click to browse
              </span>
              <span className="text-[10px] font-mono text-parchment-200/50">
                WAV, MP3, FLAC, OGG &bull; Min 2.0 s
              </span>
            </div>
          )}
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="mt-3 p-2.5 rounded bg-crimson-950/40 border border-crimson-700/60 text-xs font-mono text-crimson-300">
            [ERR]: {errorMessage}
          </div>
        )}

        {/* Analysis Result Card */}
        {result && (
          <div className="mt-4 p-4 rounded bg-void-900 border border-parchment-200/20 font-mono">
            <div className="flex items-center justify-between mb-3 border-b border-parchment-200/10 pb-2">
              <span className="text-xs text-parchment-200/70 truncate max-w-[180px]">
                {fileName}
              </span>
              <span
                className={`text-xs px-2.5 py-0.5 rounded font-bold border flex items-center gap-1.5 ${
                  result.verdict === 'REAL'
                    ? 'bg-emerald-950 text-emerald-400 border-emerald-600'
                    : 'bg-crimson-950 text-crimson-400 border-crimson-600'
                }`}
              >
                {result.verdict === 'REAL' ? (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                ) : (
                  <AlertOctagon className="w-3.5 h-3.5" />
                )}
                {result.verdict}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2 rounded bg-void-850 border border-parchment-200/10">
                <span className="text-[10px] text-parchment-200/50 block">FAKE PROB</span>
                <span
                  className={`font-bold ${
                    result.p_fake >= 0.5 ? 'text-crimson-400' : 'text-emerald-400'
                  }`}
                >
                  {(result.p_fake * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-2 rounded bg-void-850 border border-parchment-200/10">
                <span className="text-[10px] text-parchment-200/50 block">DURATION</span>
                <span className="text-parchment-200 font-bold">{result.duration_seconds}s</span>
              </div>
              <div className="p-2 rounded bg-void-850 border border-parchment-200/10">
                <span className="text-[10px] text-parchment-200/50 block">WINDOWS</span>
                <span className="text-parchment-200 font-bold">{result.windows.length}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 pt-3 border-t border-parchment-200/10 text-[10px] font-mono text-parchment-200/40 text-center">
        REST INGESTION &bull; 16 kHz RESAMPLED MONO PIPELINE
      </div>
    </div>
  )
}
