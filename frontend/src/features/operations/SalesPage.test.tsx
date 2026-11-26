import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { SalesPage } from './SalesPage'

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}))

vi.mock('../../lib/api', () => {
  const client = { get: mockGet, post: mockPost }
  return {
    api: {
      ventas: client,
      inventarios: client,
    },
    errorMessage: (error: unknown) =>
      error instanceof Error ? error.message : 'Error inesperado',
  }
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

beforeEach(() => {
  mockGet.mockReset()
  mockPost.mockReset()
  vi.spyOn(window, 'confirm').mockReturnValue(true)
})

describe('SalesPage return resolution', () => {
  it('invalidates inventory after an approved return succeeds', async () => {
    mockGet.mockImplementation((path: string) => {
      if (path === '/orders') {
        return Promise.resolve({
          data: [{
            id_pedido: 22,
            id_sede: 2,
            id_almacen: 7,
            id_cliente: 15,
            id_empleado: 5,
            fecha_pedido: '2026-01-02',
            estado: 'completado',
            total_registrado: 10,
          }],
        })
      }
      if (path === '/orders/22/returns') {
        return Promise.resolve({
          data: [{
            id_devolucion: 41,
            id_pedido: 22,
            fecha_solicitud: '2026-01-02',
            motivo: 'Motivo',
            estado: 'pendiente',
          }],
        })
      }
      if (path === '/orders/22/details') return Promise.resolve({ data: [] })
      return Promise.reject(new Error(`Unexpected GET ${path}`))
    })
    mockPost.mockResolvedValue({ data: {} })
    const invalidation = vi.fn()
    window.addEventListener('retail:inventory-updated', invalidation)

    render(
      <MemoryRouter>
        <SalesPage view="returns" />
      </MemoryRouter>,
    )

    fireEvent.click(await screen.findByRole('button', { name: 'Devoluciones' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Aprobar' }))

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/returns/41/approve')
      expect(invalidation).toHaveBeenCalledTimes(1)
      expect(screen.getByText('Devolución aprobada.')).toBeTruthy()
    })

    window.removeEventListener('retail:inventory-updated', invalidation)
  })
})
