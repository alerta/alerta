
CREATE TABLE heartbeats (
    id text NOT NULL,
    origin text NOT NULL,
    tags text[],
    type text,
    create_time timestamp,
    timeout interval,
    receive_time timestamp,
    customer text
);

CREATE UNIQUE INDEX origin_customer_key ON heartbeats (origin, COALESCE(customer, ''));
