CREATE TABLE IF NOT EXISTS `alerts` (
    `id` varchar(50) PRIMARY KEY,
    `resource` varchar(255) NOT NULL,
    `event` varchar(255) NOT NULL,
    `environment` varchar(255),
    `severity` varchar(50),
    `correlate` json,
    `status` varchar(50),
    `service` json,
    `group` varchar(255),
    `value` varchar(255),
    `text` text,
    `tags` json,
    `attributes` json,
    `origin` varchar(255),
    `type` varchar(50),
    `create_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `update_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `timeout` integer,
    `raw_data` text,
    `customer` varchar(255),
    `duplicate_count` integer,
    `repeat` boolean,
    `previous_severity` varchar(50),
    `trend_indication` varchar(50),
    `receive_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `last_receive_id` varchar(50),
    `last_receive_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `history` json
) CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `notes` (
    `id` varchar(50) PRIMARY KEY,
    `text` varchar(1000),
    `user` varchar(255),
    `attributes` json,
    `type` varchar(255) NOT NULL,
    `create_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    `update_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `alert` varchar(255),
    `customer` varchar(255)
) CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `blackouts` (
    `id` varchar(50) PRIMARY KEY,
    `priority` integer NOT NULL,
    `environment` varchar(500) NOT NULL,
    `service` json,
    `resource` varchar(500),
    `event` varchar(500),
    `group` varchar(255),
    `tags` json,
    `customer` varchar(500),
    `start_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    `end_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    `duration` integer,
    `user` varchar(500),
    `create_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `text` varchar(1000),
    `origin` varchar(500)
) CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `customers` (
    `id` varchar(50) PRIMARY KEY,
    `match` varchar(500) NOT NULL,
    `customer` varchar(500)
) CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `heartbeats` (
    `id` varchar(50) PRIMARY KEY,
    `origin` varchar(255) NOT NULL,
    `tags` json,
    `type` varchar(255),
    `create_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `timeout` integer,
    `receive_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `customer` varchar(500),
    `attributes` json
) CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `keys` (
    `id` varchar(50) PRIMARY KEY,
    `key` varchar(255) UNIQUE NOT NULL,
    `user` varchar(255) NOT NULL,
    `scopes` json,
    `text` varchar(500),
    `expire_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `count` integer,
    `last_used_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `customer` varchar(500)
) CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `metrics` (
    `group` varchar(255) NOT NULL,
    `name` varchar(255) NOT NULL,
    `title` varchar(255),
    `description` varchar(255),
    `value` integer,
    `count` integer,
    `total_time` bigint,
    `type` varchar(255) NOT NULL,
    CONSTRAINT metrics_pkey PRIMARY KEY (`group`, name, type)
) CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `perms` (
    `id` varchar(50) PRIMARY KEY,
    `match` varchar(255) UNIQUE NOT NULL,
    `scopes` json
) CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `users` (
    `id` varchar(50) PRIMARY KEY,
    `name` varchar(255),
    `email` varchar(255) UNIQUE,
    `login` varchar(255) UNIQUE NOT NULL,
    `password` varchar(255) NOT NULL,
    `status` varchar(255),
    `roles` json,
    `attributes` json,
    `create_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3) NOT NULL,
    `last_login` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `text` varchar(255),
    `update_time` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
    `email_verified` boolean,
    `hash` varchar(255)
) CHARACTER SET utf8;

CREATE TABLE IF NOT EXISTS `groups` (
    `id` varchar(50) PRIMARY KEY,
    `name` varchar(255) UNIQUE NOT NULL,
    users json,
    text varchar(255),
    tags json,
    attributes json,
    update_time datetime(3) DEFAULT CURRENT_TIMESTAMP(3)
) CHARACTER SET utf8;

DROP PROCEDURE IF EXISTS create_index;

-- DELIMITER $$
CREATE PROCEDURE create_index ()
BEGIN
    IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = database() AND TABLE_NAME='alerts' AND INDEX_NAME='env_res_evt_cust_key') THEN
        ALTER TABLE alerts ADD UNIQUE INDEX env_res_evt_cust_key USING BTREE (environment, resource, event, customer);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS WHERE TABLE_SCHEMA = database() AND TABLE_NAME='heartbeats' AND INDEX_NAME='org_cust_key') THEN
        ALTER TABLE heartbeats ADD UNIQUE INDEX org_cust_key USING BTREE (origin, customer);
    END IF;
END;

CALL create_index();
