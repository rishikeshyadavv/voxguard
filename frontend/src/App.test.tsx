import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import App from './App.tsx'

// Mock global fetch for health check
global.fetch = vi.fn().mockImplementation(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ status: 'ok', model_version: 'stub' }),
  })
)

describe('App', () => {
  it('renders VoxGuard title and live telemetry section', async () => {
    render(<App />)
    expect(screen.getByText('VoxGuard')).toBeInTheDocument()
    expect(screen.getByText('Real-time Voice Deepfake Detection')).toBeInTheDocument()
    expect(screen.getByText('Live Stream Telemetry')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/Backend: ok \(model: stub\)/i)).toBeInTheDocument()
    })
  })
})

