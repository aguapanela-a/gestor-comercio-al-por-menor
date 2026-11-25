# Frontend

Aplicación React + TypeScript para el gestor comercial.

## Desarrollo

1. Copia `.env.example` a `.env` y ajusta las URLs de los servicios si es necesario.
2. Ejecuta `npm install`.
3. Ejecuta `npm run dev`.

En desarrollo, las llamadas usan rutas `/api/{servicio}` y Vite las reenvía a las URLs configuradas en `VITE_*_API_URL`. Esto evita depender de CORS en los navegadores durante el desarrollo local.

## Producción

Configura las variables `VITE_*_API_URL` con las direcciones accesibles desde el navegador y asegúrate de que cada servicio permita el origen del frontend mediante CORS, o publica el frontend detrás de un reverse proxy/gateway que enrute las solicitudes a los servicios. El proxy de Vite solo se ejecuta en desarrollo.

El servicio de Reportes se mantiene como punto de integración pendiente; esta aplicación no consulta ni modifica sus datos.
