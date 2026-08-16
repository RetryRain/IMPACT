-- Feedback table for Bytez web app (separate Neon database).
-- Run against FEEDBACK_DATABASE_URL when setting up feedback.

CREATE TABLE IF NOT EXISTS feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  message TEXT NOT NULL,
  email TEXT,
  page_url TEXT,
  user_agent TEXT
);
