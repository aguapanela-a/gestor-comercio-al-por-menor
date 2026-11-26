CREATE TABLE IF NOT EXISTS inventarios.devoluciones_venta (
    id_devolucion BIGINT PRIMARY KEY,
    id_pedido BIGINT NOT NULL CHECK (id_pedido > 0),
    id_sede INTEGER NOT NULL CHECK (id_sede > 0),
    id_almacen INTEGER NOT NULL CHECK (id_almacen > 0),
    productos JSONB NOT NULL CHECK (jsonb_typeof(productos) = 'array'),
    fecha_reintegro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE inventarios.devoluciones_venta IS
'Registro idempotente de reintegros de inventario por devoluciones aprobadas';
