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
