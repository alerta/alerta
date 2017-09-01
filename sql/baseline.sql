
CREATE TYPE history AS (
    id text,
    event text,
    severity text,
    status text,
    value text,
    text text,
    type text,
    update_time timestamp
);

CREATE TABLE alerts (
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
    attributes text[][],
    origin text,
    type text,
    create_time timestamp,
    timeout interval,
    raw_data text,
    customer text,
    duplicate_count integer,
    repeat boolean,
    previous_severity text,
    trend_indication text,
    receive_time timestamp,
    last_receive_id text,
    last_receive_time timestamp,
    history history[]
);

CREATE UNIQUE INDEX env_res_evt_cust_key ON alerts (environment, resource, event, COALESCE(customer, ''));

CREATE TABLE blackouts (
    id text PRIMARY KEY,
    priority integer NOT NULL,
    environment text NOT NULL,
    service text,
    resource text,
    event text,
    "group" text,
    tags text[],
    customer text,
    start_time timestamp NOT NULL,
    end_time timestamp NOT NULL,
    duration interval
);

CREATE TABLE customers (
    id text PRIMARY KEY,
    match text NOT NULL,
    customer text
);

CREATE TABLE heartbeats (
    id text PRIMARY KEY,
    origin text NOT NULL,
    tags text[],
    type text,
    create_time timestamp,
    timeout interval,
    receive_time timestamp,
    customer text
);

CREATE UNIQUE INDEX org_cust_key ON heartbeats (origin, COALESCE(customer, ''));

CREATE TABLE keys (
    id text PRIMARY KEY,
    key text UNIQUE NOT NULL,
    "user" text NOT NULL,
    scopes text[],
    text text,
    expire_time timestamp,
    count integer,
    last_used_time timestamp,
    customer text
);

CREATE TABLE metrics (
    "group" text,
    name text,
    title text,
    description text,
    value text,
    count integer,
    total_time interval,
    type text,
    PRIMARY KEY ("group", name, type)
);

CREATE TABLE perms (
    id text PRIMARY KEY,
    match text NOT NULL,
    scopes text[]
);

CREATE TABLE users (
    id text PRIMARY KEY,
    name text,
    email text UNIQUE NOT NULL,
    password text NOT NULL,
    role text,
    create_time timestamp NOT NULL,
    last_login timestamp,
    text text,
    email_verified boolean,
    hash text
);

