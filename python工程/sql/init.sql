CREATE TABLE IF NOT EXISTS "app" (
    id UUID NOT NULL,
    account_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL DEFAULT '',
    icon VARCHAR(255) NOT NULL DEFAULT '',
    config JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT pk_app_id PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_app_account_id ON "app" (account_id);
