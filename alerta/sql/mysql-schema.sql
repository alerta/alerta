CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(3072),
    resource LONGTEXT NOT NULL,
    event LONGTEXT NOT NULL,
    environment LONGTEXT,
    severity LONGTEXT,
    correlate json,
    status LONGTEXT,
    service json,
    `group` LONGTEXT,
    value LONGTEXT,
    `text` LONGTEXT,
    tags json,
    attributes json,
    origin LONGTEXT,
    type LONGTEXT,
    create_time timestamp DEFAULT CURRENT_TIMESTAMP,
    timeout int,
    raw_data LONGTEXT,
    customer LONGTEXT,
    duplicate_count int,
    `repeat` BOOLEAN,
    previous_severity LONGTEXT,
    trend_indication LONGTEXT,
    receive_time timestamp DEFAULT CURRENT_TIMESTAMP,
    last_receive_id LONGTEXT,
    last_receive_time timestamp DEFAULT CURRENT_TIMESTAMP,
    history json,
    PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS blackouts (
    id VARCHAR(3072),
    priority LONGTEXT NOT NULL,
    environment LONGTEXT NOT NULL,
    service json,
    resource LONGTEXT,
    event LONGTEXT,
    `group` LONGTEXT,
    tags json,
    customer LONGTEXT,
    start_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duration int,
    PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(3072),
    `match` VARCHAR(255) NOT NULL UNIQUE,
    customer TEXT,
    PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS heartbeats (
    id VARCHAR(3072),
    origin varchar(255) NOT NULL,
    tags json,
    type TEXT,
    create_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    timeout int,
    receive_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    customer varchar(255),
    PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS `keys` (
    id VARCHAR(3072),
    `key` VARCHAR(255) NOT NULL UNIQUE,
    user TEXT NOT NULL,
    scopes json,
    `text` MEDIUMTEXT,
    expire_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    count int,
    last_used_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    customer TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS metrics (
    `group` VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    title TEXT,
    description MEDIUMTEXT,
    value int,
    count int,
    total_time BIGINT,
    type VARCHAR(255) NOT NULL,
    CONSTRAINT metrics_pkey PRIMARY KEY (`group`, name, type)
);


CREATE TABLE IF NOT EXISTS perms (
    id VARCHAR(3072),
    `match` varchar(255) NOT NULL UNIQUE,
    scopes json,
    PRIMARY KEY (id)
);


CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(3072),
    name TEXT,
    email varchar(255) NOT NULL UNIQUE,
    password varchar(255) NOT NULL,
    status TEXT,
    roles json,
    attributes json,
    create_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `text` TEXT,
    update_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    email_verified BOOLEAN,
    hash TEXT,
    PRIMARY KEY (id)
);

