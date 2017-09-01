--
-- PostgreSQL database dump
--


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


CREATE TABLE alerts (
    id text NOT NULL,
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
    attributes text[],
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


CREATE TABLE blackouts (
    id text NOT NULL,
    priority integer NOT NULL,
    environment text NOT NULL,
    service text,
    resource text,
    event text,
    "group" text,
    tags text[],
    customer text,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    duration integer
);


CREATE TABLE customers (
    id text NOT NULL,
    match text NOT NULL,
    customer text
);


CREATE TABLE heartbeats (
    id text NOT NULL,
    origin text NOT NULL,
    tags text[],
    type text,
    create_time timestamp without time zone,
    timeout integer,
    receive_time timestamp without time zone,
    customer text
);


CREATE TABLE keys (
    id text NOT NULL,
    key text NOT NULL,
    "user" text NOT NULL,
    scopes text[],
    text text,
    expire_time timestamp without time zone,
    count integer,
    last_used_time timestamp without time zone,
    customer text
);


CREATE TABLE metrics (
    "group" text NOT NULL,
    name text NOT NULL,
    title text,
    description text,
    value text,
    count integer,
    total_time integer,
    type text NOT NULL
);


CREATE TABLE perms (
    id text NOT NULL,
    match text NOT NULL,
    scopes text[]
);


CREATE TABLE users (
    id text NOT NULL,
    name text,
    email text NOT NULL,
    password text NOT NULL,
    role text,
    create_time timestamp without time zone NOT NULL,
    last_login timestamp without time zone,
    text text,
    email_verified boolean,
    hash text
);


ALTER TABLE ONLY alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);


ALTER TABLE ONLY blackouts
    ADD CONSTRAINT blackouts_pkey PRIMARY KEY (id);


ALTER TABLE ONLY customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


ALTER TABLE ONLY heartbeats
    ADD CONSTRAINT heartbeats_pkey PRIMARY KEY (id);


ALTER TABLE ONLY keys
    ADD CONSTRAINT keys_key_key UNIQUE (key);


ALTER TABLE ONLY keys
    ADD CONSTRAINT keys_pkey PRIMARY KEY (id);


ALTER TABLE ONLY metrics
    ADD CONSTRAINT metrics_pkey PRIMARY KEY ("group", name, type);


ALTER TABLE ONLY perms
    ADD CONSTRAINT perms_pkey PRIMARY KEY (id);


ALTER TABLE ONLY users
    ADD CONSTRAINT users_email_key UNIQUE (email);


ALTER TABLE ONLY users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


CREATE UNIQUE INDEX env_res_evt_cust_key ON alerts USING btree (environment, resource, event, (COALESCE(customer, ''::text)));


CREATE UNIQUE INDEX org_cust_key ON heartbeats USING btree (origin, (COALESCE(customer, ''::text)));

