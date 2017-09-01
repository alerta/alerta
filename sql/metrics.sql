
CREATE TABLE metrics (
    "group" text,
    name text,
    title text,
    description text,
    value text,
    count integer,
    total_time interval,
    type text
);

ALTER TABLE ONLY metrics
    ADD CONSTRAINT group_name_type_key UNIQUE ("group", name, type);
