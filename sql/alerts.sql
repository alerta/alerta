
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
