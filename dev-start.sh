#!/bin/bash
# flask run --debugger --port 8080 --with-threads --reload --host 0.0.0.0
gunicorn -k gevent -w 4 --bind 0.0.0.0:8080 wsgi:app
