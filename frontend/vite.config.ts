import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

const services = {
  identidad: 8001,
  catalogo: 8002,
  organizacion: 8003,
  compras: 8004,
  inventarios: 8005,
  ventas: 8006,
  reportes: 8007,
} as const

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    server: {
      proxy: Object.fromEntries(
        Object.entries(services).map(([service, port]) => [
          `/api/${service}`,
          {
            target: env[`VITE_${service.toUpperCase()}_API_URL`] || `http://127.0.0.1:${port}`,
            changeOrigin: true,
            rewrite: (path: string) => path.replace(`/api/${service}`, ''),
          },
        ]),
      ),
    },
  }
})
