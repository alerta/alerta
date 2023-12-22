# Contributing


## Setup development environment

### Install database backend

Either Postgres or MongoDB need to be available.

To install Postgres on macOS run:

```bash
$ brew install postgresql
```

To install MongoDB on macOS run:

```bash
$ brew tap mongodb/brew
$ brew install mongodb-community@4.4
```

Add `mongod` to your path and run:

```bash
$ mongod --config /usr/local/etc/mongod.conf
```

### Install packages

Create a virtual environment:

```bash
$ python3 -m venv venv
```

Install package dependencies into the virtual environment:

```bash
$ venv/bin/pip install -r requirements.txt
$ venv/bin/pip install -r requirements-dev.txt
$ venv/bin/pip install -e .
```

## Run Alerta in development mode

Alerta can be run in "development mode" from the command-line:

```bash
$ alertad run
```

Test that Alerta API is working by `curl`-ing the API endpoint:

```bash
$ curl http://localhost:8080/
```
