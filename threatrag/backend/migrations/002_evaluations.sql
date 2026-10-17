-- Phase 4: persisted RAG quality scores for the Analytics page
CREATE TABLE IF NOT EXISTS evaluations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question          TEXT NOT NULL,
    answer            TEXT NOT NULL,
    faithfulness      REAL NOT NULL,
    answer_relevancy  REAL NOT NULL,
    context_precision REAL NOT NULL,
    context_recall    REAL,
    overall           REAL NOT NULL,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS evaluations_created_idx ON evaluations (created_at DESC);

-- Reports: keep critic outcome + tool trail for auditability
ALTER TABLE reports ADD COLUMN IF NOT EXISTS tool_calls JSONB DEFAULT '[]';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS iterations INTEGER DEFAULT 1;

INSERT INTO schema_migrations (version) VALUES (2) ON CONFLICT DO NOTHING;
