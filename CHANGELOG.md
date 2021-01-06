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
