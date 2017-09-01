
CREATE TABLE keys (
    id text NOT NULL,
    key text NOT NULL,
    "user" text NOT NULL,
    scopes text[],
    text text,
    expire_time timestamp,
    count integer,
    last_used_time timestamp,
    customer text
);

ALTER TABLE ONLY keys
    ADD CONSTRAINT id_pkey PRIMARY KEY (id);
