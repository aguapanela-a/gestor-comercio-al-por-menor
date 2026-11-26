CREATE TABLE IF NOT EXISTS inventarios.despachos_venta (
    id_pedido BIGINT PRIMARY KEY,
    id_sede INTEGER NOT NULL CHECK (id_sede > 0),
    id_almacen INTEGER NOT NULL CHECK (id_almacen > 0),
    productos JSONB NOT NULL CHECK (jsonb_typeof(productos) = 'array'),
    fecha_despacho TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE inventarios.despachos_venta IS
'Registro idempotente de descuentos de inventario por pedidos pagados';
