<<<<<<< HEAD

CREATE TABLE IF NOT EXISTS alerts (
    `id` varchar(255) PRIMARY KEY,
    `resource` varchar(255) NOT NULL,
    `event` varchar(255) NOT NULL,
    `environment` varchar(255),
    `severity` varchar(255),
    `correlate` json,
    `status` varchar(255),
    `service` json,
    `group` varchar(255),
    `value` varchar(255),
    `text` varchar(255),
    `tags` json,
    `attributes` json,
    `origin` varchar(255),
    `type` varchar(255),
    `create_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `timeout` integer,
    `raw_data` varchar(255),
    `customer` varchar(255),
    `duplicate_count` integer,
    `repeat` boolean,
    `previous_severity` varchar(255),
    `trend_indication` varchar(255),
    `receive_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `last_receive_id` varchar(255),
    `last_receive_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `history` json
=======
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
>>>>>>> 99d801e7302164b7bc2c453bb0fa8d8295e771a1
);


CREATE TABLE IF NOT EXISTS blackouts (
<<<<<<< HEAD
    `id` varchar(255) PRIMARY KEY,
    `priority` integer NOT NULL,
    `environment` varchar(255) NOT NULL,
    `service` json,
    `resource` varchar(255),
    `event` varchar(255),
    `group` varchar(255),
    `tags` json,
    `customer` varchar(255),
    `start_time` timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `end_time` timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `duration` integer
=======
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
>>>>>>> 99d801e7302164b7bc2c453bb0fa8d8295e771a1
);


CREATE TABLE IF NOT EXISTS customers (
<<<<<<< HEAD
    `id` varchar(255) PRIMARY KEY,
    `match` varchar(255) UNIQUE NOT NULL,
    `customer` varchar(255)
=======
    id VARCHAR(3072),
    `match` VARCHAR(255) NOT NULL UNIQUE,
    customer TEXT,
    PRIMARY KEY (id)
>>>>>>> 99d801e7302164b7bc2c453bb0fa8d8295e771a1
);


CREATE TABLE IF NOT EXISTS heartbeats (
<<<<<<< HEAD
    `id` varchar(255) PRIMARY KEY,
    `origin` varchar(255) NOT NULL,
    `tags` json,
    `type` varchar(255),
    `create_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `timeout` integer,
    `receive_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `customer` varchar(255)
=======
    id VARCHAR(3072),
    origin varchar(255) NOT NULL,
    tags json,
    type TEXT,
    create_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    timeout int,
    receive_time timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    customer varchar(255),
    PRIMARY KEY (id)
>>>>>>> 99d801e7302164b7bc2c453bb0fa8d8295e771a1
);


CREATE TABLE IF NOT EXISTS `keys` (
<<<<<<< HEAD
    `id` varchar(255) PRIMARY KEY,
    `key` varchar(255) UNIQUE NOT NULL,
    `user` varchar(255) NOT NULL,
    `scopes` json,
    `text` varchar(255),
    `expire_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `count` integer,
    `last_used_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `customer` varchar(255)
);


CREATE TABLE IF NOT EXISTS metrics (
    `group` varchar(255) NOT NULL,
    `name` varchar(255) NOT NULL,
    `title` varchar(255),
    `description` varchar(255),
    `value` integer,
    `count` integer,
    `total_time` bigint,
    `type` varchar(255) NOT NULL,
=======
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
>>>>>>> 99d801e7302164b7bc2c453bb0fa8d8295e771a1
    CONSTRAINT metrics_pkey PRIMARY KEY (`group`, name, type)
);


CREATE TABLE IF NOT EXISTS perms (
<<<<<<< HEAD
    `id` varchar(255) PRIMARY KEY,
    `match` varchar(255) UNIQUE NOT NULL,
    `scopes` json
=======
    id VARCHAR(3072),
    `match` varchar(255) NOT NULL UNIQUE,
    scopes json,
    PRIMARY KEY (id)
>>>>>>> 99d801e7302164b7bc2c453bb0fa8d8295e771a1
);


CREATE TABLE IF NOT EXISTS users (
<<<<<<< HEAD
    `id` varchar(255) PRIMARY KEY,
    `name` varchar(255),
    `email` varchar(255) UNIQUE NOT NULL,
    `password` varchar(255) NOT NULL,
    `status` varchar(255),
    `roles` json,
    `attributes` json,
    `create_time` timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `last_login` timestamp DEFAULT CURRENT_TIMESTAMP,
    `text` varchar(255),
    `update_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `email_verified` boolean,
    `hash` varchar(255)
);

DROP PROCEDURE IF EXISTS test_index;

DELIMITER $$
CREATE PROCEDURE test_index ()
BEGIN
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = 'alerting' AND TABLE_NAME='alerts' AND INDEX_NAME='env_res_evt_cust_key') THEN
    CREATE UNIQUE INDEX env_res_evt_cust_key ON alerts (environment, resource, event, customer) USING BTREE ;
END IF;

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = 'alerting' AND TABLE_NAME='heartbeats' AND INDEX_NAME='org_cust_key') THEN
    CREATE UNIQUE INDEX org_cust_key ON heartbeats (origin, customer) USING BTREE ;
END IF;
END $$
DELIMITER ;

CALL test_index();
=======
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

>>>>>>> 99d801e7302164b7bc2c453bb0fa8d8295e771a1
