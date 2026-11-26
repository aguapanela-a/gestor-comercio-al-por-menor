import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { HomePage } from './HomePage'

const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }))

vi.mock('../../lib/api', () => {
  const client = { get: mockGet }
  return {
    api: {
      identidad: client,
      catalogo: client,
      organizacion: client,
      compras: client,
      inventarios: client,
      ventas: client,
      reportes: client,
    },
    serviceUrl: (service: string) => service === 'reportes'
      ? 'https://reportes-api.gentlepebble-7ee5dbfb.mexicocentral.azurecontainerapps.io'
      : `http://127.0.0.1/${service}`,
  }
})

vi.mock('../../auth/AuthProvider', () => ({
  useAuth: () => ({ user: { nombre_completo: 'Auditor de prueba' } }),
}))

afterEach(cleanup)

beforeEach(() => {
  mockGet.mockReset()
})

function renderHome() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  )
}

describe('HomePage service health', () => {
  it('checks Reports through the real catalog endpoint and shows connected after HTTP success', async () => {
    let resolveCatalog: ((result: { data: unknown }) => void) | undefined
    mockGet.mockImplementation((path: string) => {
      if (path === '/vistas') {
        return new Promise<{ data: unknown }>((resolve) => {
          resolveCatalog = resolve
        })
      }
      return Promise.resolve({ data: { status: 'running' } })
    })

    renderHome()

    const reportRow = screen.getByText('Reportes').closest('.service-row') as HTMLElement
    expect(within(reportRow).getByText('Comprobando conexión')).toBeTruthy()
    expect(within(reportRow).getByText(/reportes-api\.gentlepebble/)).toBeTruthy()
    expect(mockGet).toHaveBeenCalledWith('/vistas', { timeout: 3500 })

    await act(async () => {
      resolveCatalog?.({ data: [] })
    })
    await waitFor(() => {
      expect(within(reportRow).getByText('Conectado')).toBeTruthy()
    })
  })

  it('shows not available when the Reports endpoint actually fails', async () => {
    mockGet.mockImplementation((path: string) => (
      path === '/vistas'
        ? Promise.reject(new Error('API no disponible'))
        : Promise.resolve({ data: { status: 'running' } })
    ))

    renderHome()

    const reportRow = screen.getByText('Reportes').closest('.service-row') as HTMLElement
    await waitFor(() => {
      expect(within(reportRow).getByText('No disponible')).toBeTruthy()
    })
  })
})
