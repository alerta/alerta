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
