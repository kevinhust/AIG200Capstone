-- Multiplayer Data Foundation
-- Adds the minimal schema required for:
-- - Weekly gym splits (matchmaking)
-- - Privacy + friend connections (who can view/fork)
-- - BYOK credentials (encrypted api_key + base_url)

-- 1) Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2) Profiles additions (matchmaking + privacy)
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS weekly_split JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS privacy_level TEXT NOT NULL DEFAULT 'friends';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'profiles_privacy_level_check'
  ) THEN
    ALTER TABLE profiles
      ADD CONSTRAINT profiles_privacy_level_check
      CHECK (privacy_level IN ('public', 'friends', 'private'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_profiles_weekly_split_gin
  ON profiles
  USING GIN (weekly_split);

-- 3) Friend connections (social graph)
CREATE TABLE IF NOT EXISTS friend_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  requester_id TEXT NOT NULL,
  addressee_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT friend_connections_no_self_check
    CHECK (requester_id <> addressee_id),
  CONSTRAINT friend_connections_status_check
    CHECK (status IN ('pending', 'accepted', 'blocked')),
  CONSTRAINT friend_connections_unique_pair
    UNIQUE (requester_id, addressee_id)
);

CREATE INDEX IF NOT EXISTS idx_friend_connections_addressee_status
  ON friend_connections (addressee_id, status);

CREATE INDEX IF NOT EXISTS idx_friend_connections_requester_status
  ON friend_connections (requester_id, status);

-- 4) Guild settings (server-wide defaults + feature flags)
CREATE TABLE IF NOT EXISTS guild_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  guild_id TEXT NOT NULL UNIQUE,
  default_privacy TEXT NOT NULL DEFAULT 'friends',
  features_enabled JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT guild_settings_default_privacy_check
    CHECK (default_privacy IN ('public', 'friends', 'private'))
);

-- 5) BYOK user/guild LLM configs (encrypted)
CREATE TABLE IF NOT EXISTS user_llm_configs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id TEXT NOT NULL,
  owner_type TEXT NOT NULL,
  provider TEXT NOT NULL,
  base_url TEXT,
  encrypted_api_key BYTEA,
  model_name TEXT,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT user_llm_configs_owner_type_check
    CHECK (owner_type IN ('user', 'guild')),
  CONSTRAINT user_llm_configs_provider_check
    CHECK (provider IN ('openai', 'anthropic', 'google', 'local', 'custom')),
  CONSTRAINT user_llm_configs_unique_owner_provider
    UNIQUE (owner_id, owner_type, provider)
);

CREATE INDEX IF NOT EXISTS idx_user_llm_configs_owner
  ON user_llm_configs (owner_id, owner_type);

CREATE INDEX IF NOT EXISTS idx_user_llm_configs_active
  ON user_llm_configs (is_active);

-- 6) pgcrypto helpers
-- NOTE: Encryption is intentionally done via RPC functions to avoid shipping plaintext
-- keys to clients. Your bot uses the Supabase service role key server-side.

-- NOTE: Supabase installs pgcrypto into the `extensions` schema, so
-- search_path must include it for pgp_sym_encrypt / pgp_sym_decrypt.

CREATE OR REPLACE FUNCTION encrypt_api_key(plain_key TEXT, passphrase TEXT)
RETURNS BYTEA
LANGUAGE SQL
SECURITY DEFINER
SET search_path = public, extensions
AS $$
  SELECT pgp_sym_encrypt(plain_key, passphrase);
$$;

CREATE OR REPLACE FUNCTION decrypt_api_key(encrypted_key BYTEA, passphrase TEXT)
RETURNS TEXT
LANGUAGE SQL
SECURITY DEFINER
SET search_path = public, extensions
AS $$
  SELECT pgp_sym_decrypt(encrypted_key, passphrase)::TEXT;
$$;

-- Optional wrapper: avoid passing BYTEA over PostgREST by decrypting server-side.
CREATE OR REPLACE FUNCTION get_user_llm_config(
  p_owner_id TEXT,
  p_owner_type TEXT,
  p_provider TEXT,
  p_passphrase TEXT
)
RETURNS TABLE (
  owner_id TEXT,
  owner_type TEXT,
  provider TEXT,
  base_url TEXT,
  model_name TEXT,
  api_key TEXT,
  is_active BOOLEAN,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = public, extensions
AS $$
  SELECT
    c.owner_id,
    c.owner_type,
    c.provider,
    c.base_url,
    c.model_name,
    CASE
      WHEN c.encrypted_api_key IS NULL THEN NULL
      ELSE decrypt_api_key(c.encrypted_api_key, p_passphrase)
    END AS api_key,
    c.is_active,
    c.created_at,
    c.updated_at
  FROM user_llm_configs AS c
  WHERE c.owner_id = p_owner_id
    AND c.owner_type = p_owner_type
    AND c.provider = p_provider
  LIMIT 1;
$$;

-- Optional wrapper: encrypt + upsert server-side in a single RPC call.
CREATE OR REPLACE FUNCTION upsert_user_llm_config(
  p_owner_id TEXT,
  p_owner_type TEXT,
  p_provider TEXT,
  p_base_url TEXT,
  p_model_name TEXT,
  p_plain_api_key TEXT,
  p_passphrase TEXT,
  p_is_active BOOLEAN DEFAULT TRUE
)
RETURNS user_llm_configs
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
  v_encrypted BYTEA;
  v_row user_llm_configs;
BEGIN
  v_encrypted := encrypt_api_key(p_plain_api_key, p_passphrase);

  INSERT INTO user_llm_configs (
    owner_id,
    owner_type,
    provider,
    base_url,
    model_name,
    encrypted_api_key,
    is_active,
    updated_at
  )
  VALUES (
    p_owner_id,
    p_owner_type,
    p_provider,
    p_base_url,
    p_model_name,
    v_encrypted,
    p_is_active,
    NOW()
  )
  ON CONFLICT (owner_id, owner_type, provider)
  DO UPDATE SET
    base_url = EXCLUDED.base_url,
    model_name = EXCLUDED.model_name,
    encrypted_api_key = EXCLUDED.encrypted_api_key,
    is_active = EXCLUDED.is_active,
    updated_at = NOW()
  RETURNING * INTO v_row;

  RETURN v_row;
END;
$$;

