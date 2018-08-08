
CREATE TABLE IF NOT EXISTS alerts (
    `id` varchar(50) PRIMARY KEY,
    `resource` varchar(500) NOT NULL,
    `event` varchar(500) NOT NULL,
    `environment` varchar(500),
    `severity` varchar(255),
    `correlate` json,
    `status` varchar(255),
    `group` varchar(255),
    `value` varchar(255),
    `text` varchar(10000),
    `attributes` json,
    `origin` varchar(255),
    `type` varchar(255),
    `create_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `timeout` integer,
    `raw_data` varchar(10000),
    `customer` varchar(500),
    `duplicate_count` integer,
    `repeat` boolean,
    `previous_severity` varchar(255),
    `trend_indication` varchar(255),
    `receive_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `last_receive_id` varchar(255),
    `last_receive_time` timestamp DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_history (
    `id` varchar(50),
    `history` json
);

CREATE TABLE IF NOT EXISTS alert_tag (
    `alert_tag_id` int  AUTO_INCREMENT DEFAULT NULL ,
    `id` varchar(50),
    `tag` varchar(50),
    CONSTRAINT alert_tag_id UNIQUE (`alert_tag_id`),
    CONSTRAINT tag_pkey PRIMARY KEY (`id`, `tag`)
);

CREATE TABLE IF NOT EXISTS alert_correlate (
    `id` varchar(50),
    `correlate` varchar(50),
    CONSTRAINT correlate_pkey PRIMARY KEY (`id`, `correlate`)
);

CREATE TABLE IF NOT EXISTS alert_service (
    `id` varchar(50),
    `service` varchar(50),
    CONSTRAINT service_pkey PRIMARY KEY (`id`, `service`)
);

CREATE TABLE IF NOT EXISTS blackouts (
    `id` varchar(50) PRIMARY KEY,
    `priority` integer NOT NULL,
    `environment` varchar(500) NOT NULL,
    `resource` varchar(500),
    `event` varchar(500),
    `group` varchar(255),
    `customer` varchar(500),
    `start_time` timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `end_time` timestamp DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `duration` integer
);

CREATE TABLE IF NOT EXISTS blackout_tag (
    `blackout_tag_id` int  AUTO_INCREMENT DEFAULT NULL ,
    `id` varchar(50),
    `tag` varchar(50),
    CONSTRAINT blackout_tag_id UNIQUE (`blackout_tag_id`),
    CONSTRAINT btag_pkey PRIMARY KEY (`id`, `tag`)
);

CREATE TABLE IF NOT EXISTS blackout_service (
    `id` varchar(50),
    `service` varchar(50),
    CONSTRAINT bservice_pkey PRIMARY KEY (`id`, `service`)
);

CREATE TABLE IF NOT EXISTS customers (
    `id` varchar(50) PRIMARY KEY,
    `match` varchar(255) UNIQUE NOT NULL,
    `customer` varchar(500)
);

CREATE TABLE IF NOT EXISTS heartbeats (
    `id` varchar(50) PRIMARY KEY,
    `origin` varchar(255) NOT NULL,
    `tags` json,
    `type` varchar(255),
    `create_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `timeout` integer,
    `receive_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `customer` varchar(500)
);

CREATE TABLE IF NOT EXISTS `keys` (
    `id` varchar(50) PRIMARY KEY,
    `key` varchar(255) UNIQUE NOT NULL,
    `user` varchar(255) NOT NULL,
    `scopes` json,
    `text` varchar(255),
    `expire_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `count` integer,
    `last_used_time` timestamp DEFAULT CURRENT_TIMESTAMP,
    `customer` varchar(500)
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
    CONSTRAINT metrics_pkey PRIMARY KEY (`group`, name, type)
);

CREATE TABLE IF NOT EXISTS perms (
    `id` varchar(50) PRIMARY KEY,
    `match` varchar(255) UNIQUE NOT NULL,
    `scopes` json
);

CREATE TABLE IF NOT EXISTS users (
    `id` varchar(50) PRIMARY KEY,
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
DROP function IF EXISTS json_string_check;


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


DELIMITER $$
CREATE FUNCTION json_string_check(parameter_id varchar(255), parameter_tag varchar(255)) RETURNS INT 
BEGIN 
IF EXISTS (SELECT * FROM alerts WHERE id REGEXP parameter_id AND JSON_SEARCH(tags,'one',parameter_tag) > 0) THEN 
    RETURN 1; 
END IF; 
RETURN 0; 
END$$

DELIMITER ;

delete from `alerts`; 
delete from `metrics`; 
delete from `users`; 
delete from `customers`; 
delete from `metrics`;
delete from `users`;
delete from `heartbeats`;
delete from `blackouts`;
delete from `blackout_tag`;
delete from `blackout_service`;
delete from `alert_history`;
delete from `alert_tag`;
delete from `alert_correlate`;
delete from `alert_service`;
