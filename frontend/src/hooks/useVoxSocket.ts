import { useCallback, useEffect, useReducer, useRef } from 'react'
import { AudioStreamer } from '../lib/audioRecorder'

export type CallState = 'NORMAL' | 'SUSPICIOUS' | 'ALERT'
export type ConnectionStatus = 'DISCONNECTED' | 'CONNECTING' | 'CONNECTED' | 'ERROR'

export interface TelemetryPoint {
  t: number
  p_fake: number
  p_smooth: number
  state: CallState
}

export interface VoxState {
  connectionStatus: ConnectionStatus
  isStreaming: boolean
  currentScore: TelemetryPoint
  history: TelemetryPoint[]
  alertActive: boolean
  lastAlertTime: number | null
  error: string | null
}

export type VoxAction =
  | { type: 'SET_STATUS'; payload: ConnectionStatus }
  | { type: 'SCORE_RECEIVED'; payload: TelemetryPoint }
  | { type: 'ALERT_TRIGGERED'; payload: { t: number; p_smooth: number } }
  | { type: 'DISMISS_ALERT' }
  | { type: 'SET_STREAMING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'RESET' }

export const initialVoxState: VoxState = {
  connectionStatus: 'DISCONNECTED',
  isStreaming: false,
  currentScore: {
    t: 0,
    p_fake: 0,
    p_smooth: 0,
    state: 'NORMAL',
  },
  history: [],
  alertActive: false,
  lastAlertTime: null,
  error: null,
}

const MAX_HISTORY_POINTS = 60

export function voxReducer(state: VoxState, action: VoxAction): VoxState {
  switch (action.type) {
    case 'SET_STATUS':
      return { ...state, connectionStatus: action.payload }

    case 'SET_STREAMING':
      return { ...state, isStreaming: action.payload }

    case 'SET_ERROR':
      return { ...state, error: action.payload }

    case 'SCORE_RECEIVED': {
      const newPoint = action.payload
      const updatedHistory = [...state.history, newPoint]
      if (updatedHistory.length > MAX_HISTORY_POINTS) {
        updatedHistory.shift()
      }
      return {
        ...state,
        currentScore: newPoint,
        history: updatedHistory,
        // If state is ALERT, ensure alert banner is also active
        alertActive: newPoint.state === 'ALERT' ? true : state.alertActive,
      }
    }

    case 'ALERT_TRIGGERED':
      return {
        ...state,
        alertActive: true,
        lastAlertTime: action.payload.t,
      }

    case 'DISMISS_ALERT':
      return {
        ...state,
        alertActive: false,
      }

    case 'RESET':
      return {
        ...initialVoxState,
        connectionStatus: state.connectionStatus,
      }

    default:
      return state
  }
}

function playAlertChime(): void {
  try {
    const AudioCtx =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
    if (!AudioCtx) return
    const ctx = new AudioCtx()
    const now = ctx.currentTime

    const osc1 = ctx.createOscillator()
    const osc2 = ctx.createOscillator()
    const gain = ctx.createGain()

    osc1.type = 'sawtooth'
    osc2.type = 'square'

    osc1.frequency.setValueAtTime(880, now) // A5
    osc1.frequency.exponentialRampToValueAtTime(440, now + 0.3)

    osc2.frequency.setValueAtTime(440, now)
    osc2.frequency.exponentialRampToValueAtTime(220, now + 0.3)

    gain.gain.setValueAtTime(0.15, now)
    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3)

    osc1.connect(gain)
    osc2.connect(gain)
    gain.connect(ctx.destination)

    osc1.start(now)
    osc2.start(now)
    osc1.stop(now + 0.35)
    osc2.stop(now + 0.35)
  } catch {
    // Audio context may be blocked before user interaction
  }
}

export function useVoxSocket() {
  const [state, dispatch] = useReducer(voxReducer, initialVoxState)
  const socketRef = useRef<WebSocket | null>(null)
  const streamerRef = useRef<AudioStreamer | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const shouldReconnectRef = useRef<boolean>(false)

  const getWsUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    // If running in vite dev mode directly on port 5173 without proxy rewrite
    if (window.location.port === '5173') {
      return 'ws://localhost:8000/ws/mic'
    }
    return `${protocol}//${host}/ws/mic`
  }, [])

  const connectSocket = useCallback(() => {
    if (socketRef.current && (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING)) {
      return
    }

    dispatch({ type: 'SET_STATUS', payload: 'CONNECTING' })
    const ws = new WebSocket(getWsUrl())
    socketRef.current = ws

    ws.onopen = () => {
      dispatch({ type: 'SET_STATUS', payload: 'CONNECTED' })
      dispatch({ type: 'SET_ERROR', payload: null })
      // Handshake with expected sample rate
      ws.send(JSON.stringify({ sample_rate: 16000 }))
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'score') {
          dispatch({
            type: 'SCORE_RECEIVED',
            payload: {
              t: Number(data.t),
              p_fake: Number(data.p_fake),
              p_smooth: Number(data.p_smooth),
              state: data.state as CallState,
            },
          })
        } else if (data.type === 'alert') {
          playAlertChime()
          dispatch({
            type: 'ALERT_TRIGGERED',
            payload: {
              t: Number(data.t),
              p_smooth: Number(data.p_smooth),
            },
          })
        } else if (data.type === 'error') {
          dispatch({ type: 'SET_ERROR', payload: data.message })
        }
      } catch {
        // Non-JSON or binary frame
      }
    }

    ws.onerror = () => {
      dispatch({ type: 'SET_STATUS', payload: 'ERROR' })
    }

    ws.onclose = () => {
      dispatch({ type: 'SET_STATUS', payload: 'DISCONNECTED' })
      socketRef.current = null

      if (shouldReconnectRef.current) {
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connectSocket()
        }, 2000)
      }
    }
  }, [getWsUrl])

  const startStreaming = useCallback(async () => {
    try {
      dispatch({ type: 'SET_ERROR', payload: null })
      shouldReconnectRef.current = true

      connectSocket()

      if (!streamerRef.current) {
        streamerRef.current = new AudioStreamer()
      }

      await streamerRef.current.start((pcmChunk) => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          socketRef.current.send(pcmChunk)
        }
      })

      dispatch({ type: 'SET_STREAMING', payload: true })
    } catch (err) {
      dispatch({
        type: 'SET_ERROR',
        payload: err instanceof Error ? err.message : 'Microphone access denied or unavailable',
      })
      dispatch({ type: 'SET_STREAMING', payload: false })
    }
  }, [connectSocket])

  const stopStreaming = useCallback(() => {
    shouldReconnectRef.current = false
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (streamerRef.current) {
      streamerRef.current.stop()
    }

    if (socketRef.current) {
      socketRef.current.close()
      socketRef.current = null
    }

    dispatch({ type: 'SET_STREAMING', payload: false })
    dispatch({ type: 'SET_STATUS', payload: 'DISCONNECTED' })
  }, [])

  const dismissAlert = useCallback(() => {
    dispatch({ type: 'DISMISS_ALERT' })
  }, [])

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' })
  }, [])

  useEffect(() => {
    return () => {
      shouldReconnectRef.current = false
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (streamerRef.current) {
        streamerRef.current.stop()
      }
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [])

  return {
    ...state,
    startStreaming,
    stopStreaming,
    dismissAlert,
    reset,
  }
}
