CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS convocatorias (
    id SERIAL PRIMARY KEY,
    document_id TEXT UNIQUE,
    cuce TEXT,
    entidad TEXT,
    tipo_contratacion TEXT,
    modalidad TEXT,
    objeto_contratacion TEXT,
    estado TEXT,
    fecha_publicacion DATE NULL,
    fecha_presentacion DATE NULL,
    archivos_disponibles TEXT NULL,
    ficha_url TEXT NULL,
    corpus_variant TEXT NOT NULL DEFAULT 'base',
    texto_rag TEXT NOT NULL,
    metadata_json JSONB NULL,
    embedding VECTOR(384) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE convocatorias
    ADD COLUMN IF NOT EXISTS corpus_variant TEXT NOT NULL DEFAULT 'base';

CREATE UNIQUE INDEX IF NOT EXISTS ux_convocatorias_document_id
    ON convocatorias (document_id);

CREATE INDEX IF NOT EXISTS ix_convocatorias_cuce
    ON convocatorias (cuce);

CREATE INDEX IF NOT EXISTS ix_convocatorias_entidad
    ON convocatorias (entidad);

CREATE INDEX IF NOT EXISTS ix_convocatorias_tipo_contratacion
    ON convocatorias (tipo_contratacion);

CREATE INDEX IF NOT EXISTS ix_convocatorias_modalidad
    ON convocatorias (modalidad);

CREATE INDEX IF NOT EXISTS ix_convocatorias_estado
    ON convocatorias (estado);

CREATE INDEX IF NOT EXISTS ix_convocatorias_corpus_variant
    ON convocatorias (corpus_variant);

CREATE INDEX IF NOT EXISTS ix_convocatorias_embedding
    ON convocatorias
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
