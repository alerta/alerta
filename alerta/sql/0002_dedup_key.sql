ALTER TABLE alerts
    ADD COLUMN dedup_key text,
    ADD COLUMN key_source text,
    ADD COLUMN correlate_key text;

UPDATE alerts
   SET dedup_key = jsonb_build_array(resource, event)::text,
       key_source = 'template',
       correlate_key = jsonb_build_array(resource)::text;

ALTER TABLE alerts
    ALTER COLUMN dedup_key SET NOT NULL,
    ALTER COLUMN key_source SET NOT NULL,
    ADD CONSTRAINT alerts_key_source_check CHECK (key_source IN ('sender', 'template'));

CREATE UNIQUE INDEX alerts_env_cust_dedup_key ON alerts (environment, customer, dedup_key) NULLS NOT DISTINCT;
CREATE INDEX alerts_env_cust_correlate_key ON alerts (environment, customer, correlate_key);
DROP INDEX env_res_evt_cust_key;
