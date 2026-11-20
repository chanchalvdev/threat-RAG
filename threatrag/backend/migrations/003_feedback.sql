-- Phase 10: analyst feedback on answers and reports, and reports sent back for more research
CREATE TABLE IF NOT EXISTS feedback (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject     TEXT NOT NULL,                      -- identity.sub of the analyst
    target      TEXT NOT NULL CHECK (target IN ('answer', 'report')),
    target_id   TEXT NOT NULL,                      -- report id, or "<session id>:<turn>" for a chat answer
    rating      SMALLINT NOT NULL CHECK (rating IN (-1, 1)),
    note        TEXT NOT NULL DEFAULT '',
    question    TEXT NOT NULL DEFAULT '',
    answer      TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (subject, target, target_id)             -- a second vote replaces the first
);

CREATE INDEX IF NOT EXISTS feedback_created_idx ON feedback (created_at DESC);

ALTER TABLE reports ADD COLUMN IF NOT EXISTS parent_id UUID REFERENCES reports(id) ON DELETE SET NULL;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS analyst_gaps TEXT;

INSERT INTO schema_migrations (version) VALUES (3) ON CONFLICT DO NOTHING;
