BEGIN;

CREATE TABLE identidad.roles_aplicacion (
    id_rol SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo VARCHAR(32) NOT NULL UNIQUE
);

CREATE TABLE identidad.usuarios_roles (
    id_usuario INTEGER NOT NULL,
    id_rol SMALLINT NOT NULL,
    asignado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT usuarios_roles_pk PRIMARY KEY (id_usuario, id_rol),
    CONSTRAINT usuarios_roles_usuario_fk
        FOREIGN KEY (id_usuario)
        REFERENCES identidad.usuarios (id_usuario)
        ON DELETE RESTRICT,
    CONSTRAINT usuarios_roles_rol_fk
        FOREIGN KEY (id_rol)
        REFERENCES identidad.roles_aplicacion (id_rol)
        ON DELETE RESTRICT
);

INSERT INTO identidad.roles_aplicacion (codigo)
VALUES ('auditor'), ('administrador')
ON CONFLICT (codigo) DO NOTHING;

COMMIT;
