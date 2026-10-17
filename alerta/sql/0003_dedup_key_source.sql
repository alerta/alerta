DROP INDEX alerts_env_cust_dedup_key;
CREATE UNIQUE INDEX alerts_env_cust_dedup_key ON alerts (environment, customer, key_source, dedup_key) NULLS NOT DISTINCT;
