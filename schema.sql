CREATE TABLE IF NOT EXISTS customers (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name       TEXT NOT NULL,
    phone      TEXT NOT NULL UNIQUE,                         -- no duplicate phone numbers
    status     TEXT NOT NULL DEFAULT 'lead'
               CHECK (status IN ('lead', 'active', 'inactive')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()            -- filled in automatically
);

CREATE TABLE IF NOT EXISTS messages (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL
                REFERENCES customers (id) ON DELETE CASCADE, -- deleting a customer deletes their chat
    direction   TEXT NOT NULL
                CHECK (direction IN ('incoming', 'outgoing')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_messages_customer ON messages (customer_id, id);

-- Supabase exposes public tables through its own public API (using the "anon" key).
-- Turning on Row Level Security with NO policies blocks that API completely.
-- Our backend connects directly as the database owner, which bypasses RLS, so it keeps working.
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages  ENABLE ROW LEVEL SECURITY;
