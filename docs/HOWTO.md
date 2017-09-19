
SQL Tips
--------

```
alerta5=# select h.* from alerts, unnest(history) as h;
                  id                  | event  | severity | status | value | text |   type   |       update_time
--------------------------------------+--------+----------+--------+-------+------+----------+-------------------------
 4e487d08-74ff-448b-a054-eb080c814a60 | event1 | major    | None   | n/a   | test | severity | 2017-09-05 23:01:21.053
 9eeeb5da-0045-48bb-a3ee-a265b648393a | e2     | major    | None   | n/a   | test | severity | 2017-09-05 23:31:58.816
```
