
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
            "user" text,
            timeout integer
        );
    ELSE
        BEGIN
            ALTER TYPE history ADD ATTRIBUTE "user" text CASCADE;
        EXCEPTION
            WHEN duplicate_column THEN RAISE NOTICE 'column "user" already exists in history type.';
        END;
        BEGIN
            ALTER TYPE history ADD ATTRIBUTE timeout integer CASCADE;
        EXCEPTION
            WHEN duplicate_column THEN RAISE NOTICE 'column "timeout" already exists in history type.';
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

CREATE TABLE IF NOT EXISTS notes (
    id text PRIMARY KEY,
    text text,
    "user" text,
    attributes jsonb,
    type text NOT NULL,
    create_time timestamp without time zone NOT NULL,
    update_time timestamp without time zone,
    alert text,
    customer text
);


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
    WHEN duplicate_column THEN RAISE NOTICE 'column "create_time" already exists in blackouts.';
END$$;

DO $$
BEGIN
    ALTER TABLE blackouts ADD COLUMN text text;
EXCEPTION
    WHEN duplicate_column THEN RAISE NOTICE 'column "text" already exists in blackouts.';
END$$;

DO $$
BEGIN
    ALTER TABLE blackouts ADD COLUMN origin text;
EXCEPTION
    WHEN duplicate_column THEN RAISE NOTICE 'column "origin" already exists in blackouts.';
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

DO $$
BEGIN
    ALTER TABLE heartbeats ADD COLUMN attributes jsonb;
EXCEPTION
    WHEN duplicate_column THEN RAISE NOTICE 'column "attributes" already exists in heartbeats.';
END$$;


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
    WHEN duplicate_column THEN RAISE NOTICE 'column "login" already exists in users.';
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


CREATE TABLE IF NOT EXISTS customer_rules (
    id SERIAL PRIMARY KEY,
    customer_id text,
    rules text[],
    is_active boolean,
    name text
);


CREATE TABLE IF NOT EXISTS customer_channels (
    id SERIAL PRIMARY KEY,
    customer_id text,
    name text,
    channel_type text,
    properties jsonb
);


CREATE TABLE IF NOT EXISTS customer_channel_rules_map(
    id SERIAL PRIMARY KEY,
    channel_id int,
    rule_id int,
    FOREIGN KEY (channel_id) REFERENCES customer_channels(id),
    FOREIGN KEY (rule_id) REFERENCES customer_rules(id)
);

CREATE TABLE IF NOT EXISTS event_log(
    id SERIAL PRIMARY KEY,
    event_name text,
    resource text,
    customer_id text,
    environment text,
    event_properties jsonb,
    channel_id int,
    FOREIGN KEY(channel_id) REFERENCES customer_channels(id)
);


CREATE TABLE IF NOT EXISTS worker_event_id_map(
    id SERIAL PRIMARY KEY,
    worker_id text,
    event_name text,
    resource text,
    customer_id text,
    channel_id int,
    environment text,
    events int[],
    last_heart_beat_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS worker_failed_deliveries(
    id SERIAL PRIMARY KEY,
    worker_id text,
    error text,
    event_properties jsonb,
    channel_properties jsonb,
    created_at timestamp
);

ALTER TABLE IF EXISTS alerts add if not exists enriched_data jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS env_res_evt_cust_key ON alerts USING btree (environment, resource, event, (COALESCE(customer, ''::text)));


CREATE UNIQUE INDEX IF NOT EXISTS org_cust_key ON heartbeats USING btree (origin, (COALESCE(customer, ''::text)));

CREATE UNIQUE INDEX IF NOT EXISTS event_name_resource_customer_id_channel_id ON worker_event_id_map USING btree (event_name,resource,customer_id,channel_id,environment);

INSERT INTO CUSTOMER_CHANNELS(id) values(0) ON CONFLICT DO NOTHING;
delete from customer_channels where id=0;
alter table if exists customer_channels add if not exists is_active boolean not null default true;
alter table if exists customer_channels add if not exists system_added boolean not null default false;
create unique index if not exists cust_channel_sys_added on customer_channels(customer_id) where system_added=true;
alter table if exists event_log add if not exists channel_type text;
alter table if exists worker_event_id_map add if not exists channel_type text;

CREATE TABLE IF NOT EXISTS developer_channels (
    id SERIAL PRIMARY KEY,
    name text,
    notify_on text,
    channel_type text,
    is_active boolean not null default true,
    properties jsonb
);

alter table if exists alerts add if not exists properties jsonb;

CREATE TABLE IF NOT EXISTS suppression_rules(
    id SERIAL PRIMARY KEY,
    name text,
    is_active boolean not null default true,
    properties jsonb
);

CREATE TABLE IF NOT EXISTS customer_suppression_rules(
    id SERIAL PRIMARY KEY,
    name text,
    customer_id text,
    is_active boolean not null default true,
    properties jsonb
);