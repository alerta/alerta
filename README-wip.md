
Alerta 5
========

Development
-----------

```
$ git clone ...
$ cd alerta5
$ export DATABASE_ENGINE=mongodb
$ export FLASK_APP=alerta/api.py
$ export SENTRY_DSN=https://8b56098250544fb78b9578d8af2a7e13:fa9d628da9c4459c922293db72a3203f@sentry.io/153768
$ flask run --debugger --reload
```

or

```
$ FLASK_APP=alerta/api.py flask run --debugger --port 8080 --with-threads --reload
```

or

```
$ alertad run --port 8080 --reload
```


```
$ FLASK_APP=alerta/api.py DATABASE_ENGINE=postgres flask run --debugger --port 8080 --with-threads --reload
```

To do
-----
1. tests to ensure API compat - controller, model, db?
2. auto-setup mongo
3. auto-setup es
4. auto-setup postgres
5. logging
6. debug
7. wsgi
9. auth
10. docs - postgres db setup ?


Testing
-------
to test with different database backends
$ export DATABASE_ENGINE=elasticsearch
$ nosetests

Postgres Installation
---------------------
```
$ createdb alerta5
$ flyway migrate
```

