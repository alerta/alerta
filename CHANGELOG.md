## v9.0.1 (2023-06-22)

### Feat

- Add support for ACTION_UNACK to ISA 18.2 alarm model (#1715)
- add db schema (#1839)

### Fix

- `token_endpoint_auth_methods_supported` is optional (#1856)

## v9.0.0 (2023-03-17)

### Feat

- Add support for AuthProxy auth (#1657)
- show/hide API server version info (#1821)
- **plugin**: add alertname in labels when annotations.alertname (#1801)
- Add userAgent to audit log (#1656)

### Fix

- Bulk operations did not work properly (#1825)
- Replace FLASK_ENV with FLASK_DEBUG (#1824)
- Change ORDER BY no-op for Postgres 15 (#1820)
- **security**: do not expose exception errors to end users (#1811)
- **auth**: auth bypass via registering when AUTH_PROVIDER != basic (#1782)
- **plugin**: fixes an issue if the last plugin in the order (#1798)
- Do not 400 error if content type not application/json (#1756)
- Keycloak url base (#1683)
- Audit log should handle empty body on http delete (#1655)

### Refactor

- **db**: Use Psql 9.6 syntax for ADD COLUMN (#1653)

### Perf

- Add load test workflow

## v8.7.0 (2021-12-06)

## v8.6.5 (2021-12-05)

### Feat

- Support all OpenID client_secret_* token endpoint auth methods (#1641)

### Fix

- Switch docker build from alpine to debian buster
- Empty blackout values should be null (#1643)
- Allow unack when status set to ack in plugin (#1642)
- Do not hardcode inform severity (#1640)
- Housekeeping config variable precedence (#1639)
- **deps**: PyMongo 4.0 is currently not supported (#1636)

## v8.6.4 (2021-12-01)

### Feat

- Optionally print warnings if db create fails (#1627)
- Use GitHub teams for role lookup (#1625)

### Fix

- Customer lookup failed when no user email (#1629)
- special handling of sorting by custom attributes (#1628)

## v8.6.3 (2021-11-25)

## v8.6.2 (2021-11-21)

## v8.6.1 (2021-11-20)

### Feat

- add uptime stat to prometheus metrics (#1546)

## v8.6.0 (2021-05-20)

### Refactor

- convert formatted strings to f-strings (more) (#1522)
- convert tests to use f-strings (#1521)
- convert formatted strings to f-strings (#1520)

### Feat

- add escalate severity custom action plugin (#1519)
- Add support for user-defined API key (#1518)
- log dismissing notes to alert history (#1507)
- add default blackout duration to config endpoint (#1506)
- support readonly users (#1505)

### Fix

- change housekeeping delete threshold to seconds (#1508)
- config setting default environment for webhooks (#1510)
- read LDAP_BIND_PASSWORD from environment variable (#1509)

## v8.5.0 (2021-04-18)

### Fix

- **grafana**: ensure tags work on multi timeseries alert (#1450) (#1490)
- add related id to note reponse (#1499)
- **deps**: bump lxml from 4.6.2 to 4.6.3 (#1486)

### Refactor

- create "query builders" for all data models (#1446)

### Feat

- support custom top10 report sizes (#1498)
- add alert origin to blackout options (#1497)
- add support for custom auth scopes (#1479)

## v8.4.1 (2021-02-28)

### Fix

- **deps**: bump multiple package dependencies (#1470)

## v8.4.0 (2021-02-27)

### Fix

- **auth**: HMAC was falling thru to catchall if auth required (#1470)
- **tests**: enforce authentication for forwarder test (#1471)
- **deps**: update PyJWT to v2.0.0 (#1441)
- request filter fixes in logging.py (#1442)

### Refactor

- use more enums and class properties (#1444)

### Feat

- **plugin,webhook**: Add support for custom error responses (#1466)
- add pagination support to collection responses (#1443)
- **plugin**: add timeout policy plugin to enforce ack and shelve timeouts (#1410)

## v8.3.3 (2021-01-06)

### Fix

- move root logger config key back to top level (#1438)

## v8.3.2 (2021-01-02)

### Fix

- log level not set correctly if DEBUG enabled (#1437)
- do not override envvar config for GitLab and Keycloak (#1431)

## v8.3.1 (2020-12-13)

### Fix

- **search**: use phrase token when searching arrays (#1426)
- **tests**: only temporarily modify the os.environ (#1423)
- **build**: run tests against correct branch
- read built-in plugin config from env vars (#1422)

### Refactor

- **config**: simplify config settings from env vars (#1424)

## v8.3.0 (2020-12-12)

### Feat

- add allowed environments to config endpoint (#1421)
- add colors for Ack and Shelved statuses (#1420)
- add syslog logging output format (#1417)

### Fix

- remove redundant logging messages
- use string enumerated types where possible (#1419)
- add "X-Request-ID" as CORS header (#1418)
- add requestId to error responses (#1415)
- **webhook**: set alert status from action, not directly (#1409)
- **mongodb**: optional query for raw_data and history (#1408)
- **postgres**: optional query for raw_data and history (#1407)
- set alert heartbeat timeout from alert timeout

### Perf

- **db**: Do not query for rawData or history if not required
