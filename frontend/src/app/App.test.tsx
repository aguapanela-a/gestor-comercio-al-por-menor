import { MemoryRouter } from 'react-router-dom'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { App } from './App'

vi.mock('../auth/AuthProvider', () => ({
  useAuth: () => ({ ready: false, token: null }),
}))

describe('session loading UI', () => {
  it('renders the correctly encoded session message', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByText('Verificando sesión…')).toBeTruthy()
  })
})
