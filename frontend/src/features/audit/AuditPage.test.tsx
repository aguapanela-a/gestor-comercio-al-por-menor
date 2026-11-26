import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuditPage } from './AuditPage'

const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }))

vi.mock('../../lib/api', () => ({
  api: { identidad: { get: mockGet } },
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : 'Error inesperado',
}))

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

beforeEach(() => {
  mockGet.mockReset()
})

describe('AuditPage', () => {
  it('renders only the fields returned by the authenticated audit endpoint', async () => {
    mockGet.mockResolvedValue({
      data: [{
        id_auditoria: 42,
        id_usuario: 7,
        fecha_hora: '2026-11-25T10:30:00',
        accion: 'SELECT',
        objeto_consultado: 'reportes.vista_inventario_por_sede',
      }],
    })

    render(<AuditPage />)

    expect(await screen.findByText('reportes.vista_inventario_por_sede')).toBeTruthy()
    expect(screen.getByText('42')).toBeTruthy()
    expect(screen.getByText('7')).toBeTruthy()
    expect(screen.getByText('SELECT')).toBeTruthy()
    expect(mockGet).toHaveBeenCalledWith('/auth/audit', {
      params: { limit: 51, offset: 0 },
      signal: expect.any(AbortSignal),
    })
    expect(screen.queryByRole('button', { name: /editar|eliminar/i })).toBeNull()
  })

  it('shows empty and error states without write actions', async () => {
    mockGet.mockResolvedValueOnce({ data: [] })
    render(<AuditPage />)
    expect(await screen.findByText('No hay registros de auditoría disponibles.')).toBeTruthy()

    mockGet.mockRejectedValueOnce(new Error('Servicio de identidad no disponible'))
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    await waitFor(() => {
      expect(screen.getByText('Servicio de identidad no disponible')).toBeTruthy()
    })
    expect(screen.queryByRole('button', { name: /editar|eliminar/i })).toBeNull()
  })

  it('surfaces a failed audit write even when a read succeeds', async () => {
    mockGet.mockResolvedValue({
      data: [],
      headers: { 'x-audit-status': 'failed' },
    })
    render(<AuditPage />)

    expect(await screen.findByText(
      'Los registros se consultaron, pero no fue posible registrar esta consulta en auditoría.',
    )).toBeTruthy()
  })

  it('filters audit history and renders the recorded change details', async () => {
    mockGet.mockResolvedValue({
      data: [{
        id_auditoria: 43,
        id_usuario: 7,
        fecha_hora: '2026-11-25T10:30:00Z',
        accion: 'POST /orders',
        objeto_consultado: 'ventas.pedidos',
        microservicio: 'ventas',
        modulo: 'orders',
        tipo_objeto: 'ventas.pedidos',
        id_objeto: '{"id_pedido":21}',
        resultado: 'SUCCESS',
        metodo_http: 'POST',
        ruta: '/orders',
        direccion_ip: '127.0.0.1',
        correlation_id: 'corr-1',
        detalles: {
          operacion_bd: 'INSERT',
          cambios: { estado: { before: null, after: 'pendiente' } },
        },
        nombre_usuario: 'auditor',
        nombre_completo: 'Auditor de prueba',
      }],
    })

    render(<AuditPage />)
    expect(await screen.findByText('Auditor de prueba')).toBeTruthy()
    fireEvent.change(screen.getByLabelText('Filtrar por servicio'), {
      target: { value: 'ventas' },
    })
    fireEvent.change(screen.getByLabelText('Filtrar por acción'), {
      target: { value: 'POST' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Filtrar' }))

    await waitFor(() => {
      expect(mockGet).toHaveBeenLastCalledWith('/auth/audit', {
        params: {
          limit: 51,
          offset: 0,
          microservicio: 'ventas',
          accion: 'POST',
        },
        signal: expect.any(AbortSignal),
      })
    })
    expect(screen.getByText('Ver detalles')).toBeTruthy()
    expect(screen.getByText(/"estado"/)).toBeTruthy()
  })

  it('refreshes automatically every 30 seconds without overlapping requests', async () => {
    vi.useFakeTimers()
    mockGet.mockResolvedValue({ data: [] })
    render(<AuditPage />)

    await act(async () => {
      await Promise.resolve()
    })
    expect(mockGet).toHaveBeenCalledTimes(1)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
      await Promise.resolve()
    })
    expect(mockGet).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })
})
