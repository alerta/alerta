
CREATE TABLE users (
    id text NOT NULL,
    name text,
    email text NOT NULL,
    password text,
    role text,
    create_time timestamp,
    last_login timestamp,
    text text,
    email_verified boolean,
    hash text
);

ALTER TABLE ONLY users
    ADD CONSTRAINT id_pkey PRIMARY KEY (id),
    ADD CONSTRAINT email UNIQUE (email);
