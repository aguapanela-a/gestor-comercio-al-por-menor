import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuditPage } from './AuditPage'

const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }))

vi.mock('../../lib/api', () => ({
  api: { identidad: { get: mockGet } },
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : 'Error inesperado',
}))

afterEach(cleanup)

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
})
