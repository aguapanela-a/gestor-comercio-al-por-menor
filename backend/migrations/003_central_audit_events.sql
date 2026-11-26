
BEGIN;

-- Ampliar las columnas existentes para soportar auditoría centralizada.
ALTER TABLE identidad.auditoria_accesos
    ALTER COLUMN id_usuario DROP NOT NULL,
    ALTER COLUMN accion TYPE VARCHAR(120),
    ALTER COLUMN objeto_consultado TYPE VARCHAR(255);

-- Incorporar los campos del nuevo sistema de auditoría.
-- Los registros históricos quedan identificados como legacy,
-- porque no conocemos con certeza su microservicio de origen.
ALTER TABLE identidad.auditoria_accesos
    ADD COLUMN IF NOT EXISTS event_id UUID,
    ADD COLUMN IF NOT EXISTS microservicio VARCHAR(40) NOT NULL DEFAULT 'legacy',
    ADD COLUMN IF NOT EXISTS modulo VARCHAR(80) NOT NULL DEFAULT 'legacy',
    ADD COLUMN IF NOT EXISTS tipo_objeto VARCHAR(160),
    ADD COLUMN IF NOT EXISTS id_objeto TEXT,
    ADD COLUMN IF NOT EXISTS resultado VARCHAR(16) NOT NULL DEFAULT 'SUCCESS',
    ADD COLUMN IF NOT EXISTS metodo_http VARCHAR(12),
    ADD COLUMN IF NOT EXISTS ruta VARCHAR(255),
    ADD COLUMN IF NOT EXISTS direccion_ip VARCHAR(45),
    ADD COLUMN IF NOT EXISTS correlation_id UUID,
    ADD COLUMN IF NOT EXISTS detalles JSONB NOT NULL DEFAULT '{}'::JSONB;

-- Garantizar idempotencia de los eventos.
CREATE UNIQUE INDEX IF NOT EXISTS auditoria_accesos_event_id_uidx
    ON identidad.auditoria_accesos (event_id);

-- Índice para consultar auditorías cronológicamente.
CREATE INDEX IF NOT EXISTS auditoria_accesos_fecha_id_idx
    ON identidad.auditoria_accesos (fecha_hora DESC, id_auditoria DESC);

-- Índice para filtrar por servicio, módulo y resultado.
CREATE INDEX IF NOT EXISTS auditoria_accesos_filtros_idx
    ON identidad.auditoria_accesos (
        microservicio,
        modulo,
        resultado,
        fecha_hora DESC
    );

-- Restringir los resultados permitidos.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'identidad.auditoria_accesos'::regclass
          AND conname = 'auditoria_accesos_resultado_check'
    ) THEN
        ALTER TABLE identidad.auditoria_accesos
            ADD CONSTRAINT auditoria_accesos_resultado_check
            CHECK (resultado IN ('SUCCESS', 'FAILURE', 'DENIED'));
    END IF;
END;
$$;

COMMIT;
