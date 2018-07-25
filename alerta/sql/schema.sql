
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
        update_time timestamp without time zone
    );
    END IF;
END$$;


CREATE TABLE alerts (
    id TINYTEXT,
    resource LONGTEXT NOT NULL,
    event LONGTEXT NOT NULL,
    environment LONGTEXT,
    severity LONGTEXT,
    correlate text[],
    status LONGTEXT,
    service text[],
    group LONGTEXT,
    value LONGTEXT,
    text LONGTEXT,
    tags text[],
    attributes json,
    origin LONGTEXT,
    type LONGTEXT,
    create_time timestamp,
    timeout int,
    raw_data LONGTEXT,
    customer LONGTEXT,
    duplicate_count int,
    repeat BOOLEAN,
    previous_severity LONGTEXT,
    trend_indication LONGTEXT,
    receive_time timestamp,
    last_receive_id LONGTEXT,
    last_receive_time timestamp,
    history history[],
    PRIMARY KEY (id)
);


CREATE TABLE blackouts (
    id TINYTEXT,
    priority TEXT NOT NULL,
    environment TINYTEXT NOT NULL,
    service text[],
    resource TEXT,
    event TEXT,
    group LONGTEXT,
    tags text[],
    customer LONGTEXT,
    start_time timestamp NOT NULL,
    end_time timestamp NOT NULL,
    duration int,
    PRIMARY KEY (id)
);


CREATE TABLE customers (
    id TINYTEXT,
    match TEXT NOT NULL UNIQUE,
    customer TEXT,
    PRIMARY KEY (id)
);


CREATE TABLE heartbeats (
    id TINYTEXT,
    origin TEXT NOT NULL,
    tags text[],
    type TEXT,
    create_time timestamp,
    timeout int,
    receive_time timestamp,
    customer TEXT,
    PRIMARY KEY (id)
);


CREATE TABLE keys (
    id TINYTEXT,
    key TINYTEXT NOT NULL UNIQUE,
    user TEXT NOT NULL,
    scopes text[],
    "text" MEDIUMTEXT,
    expire_time timestamp,
    count int,
    last_used_time timestamp,
    customer TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE metrics (
    group TEXT NOT NULL,
    name TEXT NOT NULL,
    title TEXT,
    description MEDIUMTEXT,
    value int,
    count int,
    total_time int,
    type LONGTEXT NOT NULL,
    CONSTRAINT metrics_pkey PRIMARY KEY (group, name, type)
);
ALTER TABLE metrics ALTER COLUMN total_time TYPE BIGINT;


CREATE TABLE perms (
    id TINYTEXT,
    match TEXT NOT NULL UNIQUE,
    scopes text[],
    PRIMARY KEY (id)
);


CREATE TABLE users (
    id TINYTEXT,
    name TEXT,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    status TEXT,
    roles text[],
    attributes json,
    create_time timestamp NOT NULL,
    last_login timestamp,
    "text" TEXT,
    update_time timestamp,
    email_verified BOOLEAN,
    hash TEXT,
    PRIMARY KEY (id)
);


CREATE UNIQUE INDEX IF NOT EXISTS env_res_evt_cust_key ON alerts USING BTREE (environment, resource, event, (COALESCE(customer, ''::text)));


CREATE UNIQUE INDEX IF NOT EXISTS org_cust_key ON heartbeats USING BTREE (origin, (COALESCE(customer, ''::text)));

