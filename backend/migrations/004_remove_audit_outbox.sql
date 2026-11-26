BEGIN;

DO $$
DECLARE
    trigger_record RECORD;
    pending_count BIGINT;
BEGIN
    IF to_regprocedure('audit_local.capture_row_change()') IS NOT NULL THEN
        FOR trigger_record IN
            SELECT namespace.nspname AS schema_name, relation.relname AS table_name,
                   trg.tgname AS trigger_name
            FROM pg_trigger AS trg
            JOIN pg_class AS relation ON relation.oid = trg.tgrelid
            JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
            WHERE NOT trg.tgisinternal
              AND trg.tgfoid = to_regprocedure('audit_local.capture_row_change()')
        LOOP
            EXECUTE format(
                'DROP TRIGGER IF EXISTS %I ON %I.%I',
                trigger_record.trigger_name,
                trigger_record.schema_name,
                trigger_record.table_name
            );
        END LOOP;
    END IF;

    DROP FUNCTION IF EXISTS audit_local.capture_row_change();
    DROP FUNCTION IF EXISTS audit_local.safe_row(JSONB);

    IF to_regclass('audit_local.outbox') IS NOT NULL THEN
        EXECUTE 'SELECT count(*) FROM audit_local.outbox' INTO pending_count;
        IF pending_count = 0 THEN
            DROP TABLE audit_local.outbox;
        ELSE
            RAISE NOTICE
                'Retaining audit_local.outbox with % pending rows; export or reconcile them manually before cleanup.',
                pending_count;
        END IF;
    END IF;

    IF to_regnamespace('audit_local') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM pg_class AS relation
           JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
           WHERE namespace.nspname = 'audit_local'
       )
    THEN
        DROP SCHEMA audit_local;
    END IF;
END;
$$;

COMMIT;
