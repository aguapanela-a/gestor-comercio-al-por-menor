import { AxiosError, type AxiosResponse } from 'axios'
import { describe, expect, it } from 'vitest'
import { api } from './api'

describe('API client', () => {
  it('does not retry a committed write when audit persistence returns 503', async () => {
    const client = api.ventas
    const originalAdapter = client.defaults.adapter
    const requests: string[] = []

    client.defaults.adapter = async (config) => {
      requests.push(config.method ?? '')
      const response = {
        data: {
          business_operation_committed: true,
          audit_persisted: false,
          retryable: false,
        },
        status: 503,
        statusText: 'Service Unavailable',
        headers: {},
        config,
      } as AxiosResponse
      throw new AxiosError(
        'La operación se confirmó, pero falló la auditoría.',
        AxiosError.ERR_BAD_RESPONSE,
        config,
        undefined,
        response,
      )
    }

    try {
      await expect(client.post('/orders', { id_cliente: 7 })).rejects.toMatchObject({
        response: { status: 503 },
      })
      expect(requests).toEqual(['post'])
    } finally {
      client.defaults.adapter = originalAdapter
    }
  })
})
