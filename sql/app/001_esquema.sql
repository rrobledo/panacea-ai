-- Esquema de la app web (conversaciones, reportes, auditoría). Separado de public por esquema y rol.
-- Ejecutar con el rol dueño de la base (en Vercel/Neon, con POSTGRES_URL_NON_POOLING).
-- Idempotente: se puede volver a correr.

CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.migraciones (
    version     text PRIMARY KEY,
    aplicada    timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------- conversaciones
CREATE TABLE IF NOT EXISTS app.conversaciones (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario             text NOT NULL,                      -- email
    perfil              text NOT NULL,
    titulo              text NOT NULL DEFAULT '',
    estado              text NOT NULL DEFAULT 'lista'
                        CHECK (estado IN ('lista', 'en_curso', 'esperando_aclaracion')),
    tool_use_pendiente  jsonb,                              -- solicitar_aclaraciones en espera
    creada              timestamptz NOT NULL DEFAULT now(),
    actualizada         timestamptz NOT NULL DEFAULT now(),
    latido              timestamptz                         -- último avance de un turno en curso
);
CREATE INDEX IF NOT EXISTS conversaciones_usuario_idx ON app.conversaciones (usuario, actualizada DESC);

-- Historial tal como lo devuelve la Messages API. Solo se agrega al final (nunca UPDATE).
CREATE TABLE IF NOT EXISTS app.mensajes (
    conversacion_id     uuid NOT NULL REFERENCES app.conversaciones (id) ON DELETE CASCADE,
    orden               int NOT NULL,
    rol                 text NOT NULL CHECK (rol IN ('user', 'assistant', 'system')),
    contenido           jsonb NOT NULL,
    creado              timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (conversacion_id, orden)
);

-- Resultado de cada herramienta, guardado apenas termina: permite retomar un turno cortado.
CREATE TABLE IF NOT EXISTS app.pasos_herramienta (
    conversacion_id     uuid NOT NULL REFERENCES app.conversaciones (id) ON DELETE CASCADE,
    tool_use_id         text NOT NULL,
    nombre              text NOT NULL,
    argumentos          jsonb NOT NULL,
    resultado           text NOT NULL,
    es_error            boolean NOT NULL DEFAULT false,
    duracion_ms         int NOT NULL,
    creado              timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (conversacion_id, tool_use_id)
);

-- ---------------------------------------------------------------- aclaraciones y reportes
CREATE TABLE IF NOT EXISTS app.briefs (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    conversacion_id     uuid NOT NULL REFERENCES app.conversaciones (id) ON DELETE CASCADE,
    tool_use_id         text NOT NULL,
    contenido           jsonb NOT NULL,
    respuestas          jsonb,
    estado              text NOT NULL DEFAULT 'propuesto'
                        CHECK (estado IN ('propuesto', 'aprobado', 'ajustado')),
    creado              timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS app.artifacts (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo              text NOT NULL,
    tipo                text NOT NULL CHECK (tipo IN ('reporte', 'tablero', 'tabla')),
    perfil              text NOT NULL,
    autor               text NOT NULL,
    conversacion_id     uuid REFERENCES app.conversaciones (id) ON DELETE SET NULL,
    brief_id            uuid REFERENCES app.briefs (id),
    fijado              boolean NOT NULL DEFAULT false,
    version_actual      int NOT NULL DEFAULT 1,
    creado              timestamptz NOT NULL DEFAULT now(),
    actualizado         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS artifacts_perfil_idx ON app.artifacts (perfil, fijado DESC, actualizado DESC);

CREATE TABLE IF NOT EXISTS app.artifact_versions (
    artifact_id         uuid NOT NULL REFERENCES app.artifacts (id) ON DELETE CASCADE,
    version             int NOT NULL,
    html                text NOT NULL,
    nota                text NOT NULL DEFAULT '',
    contenido           jsonb NOT NULL DEFAULT '{}',        -- entrada estructurada (base de la edición)
    datos_fuente        jsonb NOT NULL DEFAULT '[]',
    tool_use_id         text UNIQUE,                        -- llamada que la creó: evita duplicados al retomar
    creado              timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (artifact_id, version)
);

-- ---------------------------------------------------------------- auditoría
CREATE TABLE IF NOT EXISTS app.auditoria_sql (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario             text NOT NULL,
    perfil              text NOT NULL,
    conversacion_id     uuid,
    herramienta         text NOT NULL,
    sql                 text,
    parametros          jsonb,
    duracion_ms         int,
    filas               int,
    error               text,
    creado              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS auditoria_sql_usuario_idx ON app.auditoria_sql (usuario, creado DESC);

CREATE TABLE IF NOT EXISTS app.uso_tokens (
    id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    usuario             text NOT NULL,
    perfil              text NOT NULL,
    conversacion_id     uuid,
    modelo              text NOT NULL,
    entrada             int NOT NULL DEFAULT 0,
    salida              int NOT NULL DEFAULT 0,
    cache_lectura       int NOT NULL DEFAULT 0,
    cache_escritura     int NOT NULL DEFAULT 0,
    costo_usd           numeric(12, 6) NOT NULL DEFAULT 0,
    creado              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS uso_tokens_usuario_idx ON app.uso_tokens (usuario, creado DESC);

-- ---------------------------------------------------------------- permisos del rol de la app
-- El rol agente_app se crea en sql/roles_perfiles.sql. Si ya existe, recibe permisos acá.
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'agente_app') THEN
        GRANT USAGE ON SCHEMA app TO agente_app;
        GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA app TO agente_app;
        GRANT UPDATE ON app.conversaciones, app.briefs, app.artifacts TO agente_app;
        GRANT DELETE ON app.conversaciones TO agente_app;
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA app TO agente_app;
    END IF;
END $$;

INSERT INTO app.migraciones (version) VALUES ('001_esquema') ON CONFLICT DO NOTHING;
