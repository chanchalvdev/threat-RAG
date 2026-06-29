-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Reports table for Phase 3 investigation persistence
CREATE TABLE IF NOT EXISTS reports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ioc         TEXT NOT NULL,
    ioc_type    TEXT NOT NULL,
    final_report TEXT NOT NULL,
    sources     JSONB DEFAULT '[]',
    ragas_scores JSONB DEFAULT '{}',
    embedding   VECTOR(768),
    session_id  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Vector similarity search index (cosine)
CREATE INDEX IF NOT EXISTS reports_embedding_idx
    ON reports USING hnsw (embedding vector_cosine_ops);

-- Fast lookup by IOC
CREATE INDEX IF NOT EXISTS reports_ioc_idx
    ON reports (ioc, ioc_type);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    applied_at  TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO schema_migrations (version) VALUES (1) ON CONFLICT DO NOTHING;
