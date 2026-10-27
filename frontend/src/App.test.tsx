import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import App from './App.tsx'

// Mock global fetch for health check probe
global.fetch = vi.fn().mockImplementation(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ status: 'ok', model_version: 'stub' }),
  })
)

// Mock ResizeObserver for Recharts ResponsiveContainer
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

describe('App HUD Dashboard', () => {
  it('renders VoxGuard cyber-gothic HUD and panels', async () => {
    render(<App />)

    // Header & Titles
    expect(screen.getByText('VoxGuard')).toBeInTheDocument()
    expect(screen.getByText(/REAL-TIME VOICE DEEPFAKE DETECTION/i)).toBeInTheDocument()

    // Streaming & Meter Controls
    expect(screen.getByText(/STREAM MIC/i)).toBeInTheDocument()
    expect(screen.getByText(/\/\/ CONFIDENCE_GAUGE/i)).toBeInTheDocument()

    // File Dropzone and Benchmarks
    expect(screen.getByText(/\/\/ FILE_ANALYSIS_DROPZONE/i)).toBeInTheDocument()
    expect(screen.getByText(/Sample Real Voice/i)).toBeInTheDocument()
    expect(screen.getByText(/Sample Cloned Voice/i)).toBeInTheDocument()

    // Health status check
    await waitFor(() => {
      expect(screen.getByText(/API: ok \(model: stub\)/i)).toBeInTheDocument()
    })
  })
})
