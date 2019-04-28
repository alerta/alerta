
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'history') THEN
        CREATE TYPE history AS (
            id text,
            event text,
            severity text,
            status text,
            value text,
            text text,
            type text,
            update_time timestamp without time zone,
            "user" text
        );
    ELSE
        BEGIN
            ALTER TYPE history ADD ATTRIBUTE "user" text CASCADE;
        EXCEPTION
            WHEN duplicate_column THEN RAISE NOTICE 'user exists in history type';
        END;
    END IF;
END$$;


CREATE TABLE IF NOT EXISTS alerts (
    id text PRIMARY KEY,
    resource text NOT NULL,
    event text NOT NULL,
    environment text,
    severity text,
    correlate text[],
    status text,
    service text[],
    "group" text,
    value text,
    text text,
    tags text[],
    attributes jsonb,
    origin text,
    type text,
    create_time timestamp without time zone,
    timeout integer,
    raw_data text,
    customer text,
    duplicate_count integer,
    repeat boolean,
    previous_severity text,
    trend_indication text,
    receive_time timestamp without time zone,
    last_receive_id text,
    last_receive_time timestamp without time zone,
    history history[]
);

DO $$
BEGIN
    ALTER TABLE alerts ADD COLUMN update_time timestamp without time zone;
EXCEPTION
    WHEN duplicate_column THEN RAISE NOTICE 'column "update_time" already exists in alerts.';
END$$;

CREATE TABLE IF NOT EXISTS blackouts (
    id text PRIMARY KEY,
    priority integer NOT NULL,
    environment text NOT NULL,
    service text[],
    resource text,
    event text,
    "group" text,
    tags text[],
    customer text,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    duration integer
);

-- Support for "IF NOT EXISTS" added to "ADD COLUMN" in Postgres 9.6
-- ALTER TABLE blackouts
-- ADD COLUMN IF NOT EXISTS "user" text,
-- ADD COLUMN IF NOT EXISTS create_time timestamp without time zone,
-- ADD COLUMN IF NOT EXISTS text text;

DO $$
BEGIN
    ALTER TABLE blackouts ADD COLUMN "user" text;
EXCEPTION
    WHEN duplicate_column THEN RAISE NOTICE 'column "user" already exists in blackouts.';
END$$;

DO $$
BEGIN
    ALTER TABLE blackouts ADD COLUMN create_time timestamp without time zone;
EXCEPTION
    WHEN duplicate_column THEN RAISE NOTICE 'column create_time already exists in blackouts.';
END$$;

DO $$
BEGIN
    ALTER TABLE blackouts ADD COLUMN text text;
EXCEPTION
    WHEN duplicate_column THEN RAISE NOTICE 'column text already exists in blackouts.';
END$$;


CREATE TABLE IF NOT EXISTS customers (
    id text PRIMARY KEY,
    match text NOT NULL,
    customer text
);

ALTER TABLE customers DROP CONSTRAINT IF EXISTS customers_match_key;


CREATE TABLE IF NOT EXISTS heartbeats (
    id text PRIMARY KEY,
    origin text NOT NULL,
    tags text[],
    type text,
    create_time timestamp without time zone,
    timeout integer,
    receive_time timestamp without time zone,
    customer text
);


CREATE TABLE IF NOT EXISTS keys (
    id text PRIMARY KEY,
    key text UNIQUE NOT NULL,
    "user" text NOT NULL,
    scopes text[],
    text text,
    expire_time timestamp without time zone,
    count integer,
    last_used_time timestamp without time zone,
    customer text
);


CREATE TABLE IF NOT EXISTS metrics (
    "group" text NOT NULL,
    name text NOT NULL,
    title text,
    description text,
    value integer,
    count integer,
    total_time integer,
    type text NOT NULL,
    CONSTRAINT metrics_pkey PRIMARY KEY ("group", name, type)
);
ALTER TABLE metrics ALTER COLUMN total_time TYPE BIGINT;


CREATE TABLE IF NOT EXISTS perms (
    id text PRIMARY KEY,
    match text UNIQUE NOT NULL,
    scopes text[]
);


CREATE TABLE IF NOT EXISTS users (
    id text PRIMARY KEY,
    name text,
    email text UNIQUE,
    password text NOT NULL,
    status text,
    roles text[],
    attributes jsonb,
    create_time timestamp without time zone NOT NULL,
    last_login timestamp without time zone,
    text text,
    update_time timestamp without time zone,
    email_verified boolean,
    hash text
);
ALTER TABLE users ALTER COLUMN email DROP NOT NULL;

DO $$
BEGIN
    ALTER TABLE users ADD COLUMN login text UNIQUE;
    UPDATE users SET login = email;
    ALTER TABLE users ALTER COLUMN login SET NOT NULL;
EXCEPTION
    WHEN duplicate_column THEN RAISE NOTICE 'column login already exists in users.';
END$$;

CREATE TABLE IF NOT EXISTS groups (
    id text PRIMARY KEY,
    name text UNIQUE NOT NULL,
    users text[],
    text text,
    tags text[],
    attributes jsonb,
    update_time timestamp without time zone
);


CREATE UNIQUE INDEX IF NOT EXISTS env_res_evt_cust_key ON alerts USING btree (environment, resource, event, (COALESCE(customer, ''::text)));


CREATE UNIQUE INDEX IF NOT EXISTS org_cust_key ON heartbeats USING btree (origin, (COALESCE(customer, ''::text)));
