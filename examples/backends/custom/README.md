Custom backends example
=======================

Provided example consists of a database backend based on standard PostgreSQL backend.

It has a very basic functionality, adding an attribute to the alert before storing it
in the database. This functionality can be achieved using plugins, it is just an example.

Custom backends must provide a class named 'Backend' that implements `alerta.database.base.Backend`.

The module providing that class must be referenced as an 'alerta.database.backends' entry-point in
python package setup.

```
   ...
    entry_points={
        'alerta.database.backends': [
            'custom = package'
        ]
    }
    ...
```

To use the custom database backend, the name used for the entry-point has to be used as schema in
`DATABASE_URL` configuration setting:

```
DATABASE_URL = "custom://user@db_server/monitoring?connect_timeout=10&application_name=alerta"
```
