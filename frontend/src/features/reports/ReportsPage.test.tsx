import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ReportsPage } from './ReportsPage'

const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }))

vi.mock('../../lib/api', () => ({
  api: { reportes: { get: mockGet } },
  errorMessage: (error: unknown) =>
    error instanceof Error ? error.message : 'Error inesperado',
}))

type TestView = {
  name: string
  schema: string
  label: string
  description: string | null
  columns: { name: string; type: string; nullable: boolean; description: string | null }[]
}

function view(name: string, label: string): TestView {
  return {
    name,
    schema: 'reportes',
    label,
    description: null,
    columns: [{ name: 'valor', type: 'text', nullable: true, description: null }],
  }
}

beforeEach(() => {
  mockGet.mockReset()
  vi.spyOn(window, 'setInterval').mockReturnValue(1)
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('ReportsPage', () => {
  it('renders every view returned by the catalog and derives columns from its rows', async () => {
    const views = Array.from({ length: 15 }, (_, index) =>
      view(`vista_reporte_${index}`, `Reporte ${index}`),
    )
    mockGet.mockImplementation(async (url: string) => (
      url === '/vistas'
        ? { data: views }
        : { data: [{ valor: `fila de ${decodeURIComponent(url.split('/').pop() ?? '')}` }] }
    ))

    render(<ReportsPage />)

    expect(await screen.findByText('Reporte 14')).toBeTruthy()
    expect(await screen.findByText('fila de vista_reporte_0')).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: 'Valor' })).toBeTruthy()
    expect(window.setInterval).toHaveBeenCalledWith(expect.any(Function), 30_000)
  })

  it('shows added views and switches away from a view removed from the catalog', async () => {
    const firstView = view('vista_inicial', 'Reporte inicial')
    const newView = view('vista_nueva', 'Reporte nuevo')
    const catalogs = [[firstView], [firstView, newView], [newView]]
    mockGet.mockImplementation(async (url: string) => (
      url === '/vistas'
        ? { data: catalogs.shift() ?? [newView] }
        : { data: [{ valor: `datos ${url.split('/').pop()}` }] }
    ))

    render(<ReportsPage />)
    expect(await screen.findByRole('heading', { name: 'Reporte inicial' })).toBeTruthy()
    expect(await screen.findByText('datos vista_inicial')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    await waitFor(() => expect(screen.getByText('Reporte nuevo')).toBeTruthy())

    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))
    await waitFor(() => {
      expect(screen.queryByText('Reporte inicial')).toBeNull()
      expect(screen.getByRole('heading', { name: 'Reporte nuevo' })).toBeTruthy()
    })
  })

  it('retains the last catalog and rows when refresh requests fail', async () => {
    const existingView = view('vista_existente', 'Reporte existente')
    let catalogCalls = 0
    let viewCalls = 0
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/vistas') {
        catalogCalls += 1
        if (catalogCalls > 1) throw new Error('Catálogo no disponible')
        return { data: [existingView] }
      }

      viewCalls += 1
      if (viewCalls > 1) throw new Error('Reporte no disponible')
      return { data: [{ valor: 'último resultado válido' }] }
    })

    render(<ReportsPage />)
    expect(await screen.findByText('último resultado válido')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }))

    expect(await screen.findByText('Catálogo no disponible')).toBeTruthy()
    expect(screen.getByText('Reporte no disponible')).toBeTruthy()
    expect(screen.getByText('último resultado válido')).toBeTruthy()
    expect(screen.getAllByText('Reporte existente')).toHaveLength(2)
  })

  it('filters the catalog by a readable report name', async () => {
    mockGet.mockResolvedValue({
      data: [
        view('vista_ventas', 'Ventas mensuales'),
        view('vista_inventario', 'Inventario por sede'),
      ],
    })

    render(<ReportsPage />)
    const search = await screen.findByRole('searchbox', { name: 'Buscar reportes' })
    fireEvent.change(search, { target: { value: 'inventario' } })

    expect(screen.getByRole('button', { name: /Inventario por sede/ })).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Ventas mensuales/ })).toBeNull()
  })
})
