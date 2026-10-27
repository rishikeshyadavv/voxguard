import { describe, it, expect } from 'vitest'
import {
  voxReducer,
  initialVoxState,
  VoxState,
  TelemetryPoint,
} from './useVoxSocket'

describe('voxReducer', () => {
  it('returns default initial state', () => {
    expect(initialVoxState.connectionStatus).toBe('DISCONNECTED')
    expect(initialVoxState.isStreaming).toBe(false)
    expect(initialVoxState.history).toEqual([])
    expect(initialVoxState.alertActive).toBe(false)
  })

  it('handles SET_STATUS action', () => {
    const nextState = voxReducer(initialVoxState, {
      type: 'SET_STATUS',
      payload: 'CONNECTED',
    })
    expect(nextState.connectionStatus).toBe('CONNECTED')
  })

  it('handles SET_STREAMING action', () => {
    const nextState = voxReducer(initialVoxState, {
      type: 'SET_STREAMING',
      payload: true,
    })
    expect(nextState.isStreaming).toBe(true)
  })

  it('handles SCORE_RECEIVED and maintains rolling history buffer capped at 60 points', () => {
    let state = initialVoxState

    // Ingest 65 points sequentially
    for (let i = 1; i <= 65; i++) {
      const point: TelemetryPoint = {
        t: i * 0.5,
        p_fake: 0.1,
        p_smooth: 0.12,
        state: 'NORMAL',
      }
      state = voxReducer(state, {
        type: 'SCORE_RECEIVED',
        payload: point,
      })
    }

    expect(state.history.length).toBe(60)
    // Oldest 5 points (t = 0.5 to 2.5) dropped, oldest remaining is t = 3.0 (i=6)
    expect(state.history[0].t).toBe(3.0)
    // Most recent is t = 32.5 (i=65)
    expect(state.history[59].t).toBe(32.5)
    expect(state.currentScore.t).toBe(32.5)
  })

  it('handles ALERT_TRIGGERED and activates alert banner', () => {
    const stateWithAlert = voxReducer(initialVoxState, {
      type: 'ALERT_TRIGGERED',
      payload: { t: 14.5, p_smooth: 0.88 },
    })

    expect(stateWithAlert.alertActive).toBe(true)
    expect(stateWithAlert.lastAlertTime).toBe(14.5)
  })

  it('handles DISMISS_ALERT', () => {
    const activeAlertState: VoxState = {
      ...initialVoxState,
      alertActive: true,
      lastAlertTime: 12.0,
    }

    const dismissedState = voxReducer(activeAlertState, { type: 'DISMISS_ALERT' })
    expect(dismissedState.alertActive).toBe(false)
    expect(dismissedState.lastAlertTime).toBe(12.0)
  })

  it('handles RESET', () => {
    const populatedState: VoxState = {
      ...initialVoxState,
      connectionStatus: 'CONNECTED',
      history: [{ t: 2.0, p_fake: 0.5, p_smooth: 0.5, state: 'SUSPICIOUS' }],
      alertActive: true,
      error: 'Some error',
    }

    const resetState = voxReducer(populatedState, { type: 'RESET' })
    expect(resetState.history).toEqual([])
    expect(resetState.alertActive).toBe(false)
    expect(resetState.error).toBe(null)
    expect(resetState.connectionStatus).toBe('CONNECTED') // Preserves connection status
  })
})
