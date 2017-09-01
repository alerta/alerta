
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
    start_time timestamp NOT NULL,
    end_time timestamp NOT NULL,
    duration interval
);
