import json
import logging
import os
from logging.config import dictConfig

import flask
import yaml
from flask import Flask, g, request


class Logger:

    def __init__(self, app: Flask = None) -> None:
        self.app = None
        if app:
            self.setup_logging(app)

    def setup_logging(self, app: Flask) -> None:

        from flask.logging import default_handler  # noqa
        # app.logger.removeHandler(default_handler)

        def open_file(filename, mode='r'):
            path = os.path.join(os.path.dirname(__file__), filename)
            return open(path, mode)

        log_config_file = os.path.expandvars(os.path.expanduser(app.config['LOG_CONFIG_FILE']))
        log_level = 'DEBUG' if app.debug else app.config['LOG_LEVEL']

        if os.path.exists(log_config_file):
            with open_file(log_config_file) as f:
                dictConfig(yaml.safe_load(f.read()))
        else:
            if app.config['LOG_FORMAT'] in ['default', 'simple', 'verbose', 'json']:
                log_format = app.config['LOG_FORMAT']
                custom_format = ''  # not used
            else:
                log_format = 'custom'
                custom_format = app.config['LOG_FORMAT']

            if 'file' in app.config['LOG_HANDLERS']:
                log_file = os.path.expandvars(os.path.expanduser(app.config['LOG_FILE']))
            else:
                log_file = '/dev/null'

            dictConfig({
                'version': 1,
                'disable_existing_loggers': False,
                'formatters': {
                    'default': {
                        '()': 'alerta.utils.logging.CustomFormatter'
                    },
                    'simple': {
                        'format': '%(levelname)s %(message)s'
                    },
                    'verbose': {
                        'format': '%(asctime)s - %(name)s[%(process)d]: %(levelname)s - %(message)s [in %(pathname)s:%(lineno)d]'
                    },
                    'json': {
                        '()': 'alerta.utils.logging.JSONFormatter'
                    },
                    'custom': {
                        'format': custom_format
                    }
                },
                'filters': {
                    'requests': {
                        '()': 'alerta.utils.logging.RequestFilter',
                        'methods': app.config['LOG_METHODS']
                    }
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': log_format,
                        'level': log_level,
                        'filters': ['requests'],
                        'stream': 'ext://sys.stdout'
                    },
                    'file': {
                        'class': 'logging.handlers.RotatingFileHandler',
                        'formatter': log_format,
                        'filters': ['requests'],
                        'filename': log_file,
                        'maxBytes': app.config['LOG_MAX_BYTES'],
                        'backupCount': app.config['LOG_BACKUP_COUNT']
                    },
                    'wsgi': {
                        'class': 'logging.StreamHandler',
                        'formatter': log_format,
                        'filters': ['requests'],
                        'stream': 'ext://flask.logging.wsgi_errors_stream'
                    }
                },
                'root': {
                    'level': log_level,
                    'handlers': app.config['LOG_HANDLERS']
                }
            })


class RequestFilter(logging.Filter):

    def __init__(self, methods=None):
        self.methods = methods or []
        super().__init__()

    def filter(self, record):

        if hasattr(record, 'method'):
            if record.method in self.methods:
                return True
        else:
            return True


class CustomFormatter(logging.Formatter):

    def __init__(self):

        self.formatters = {
            'alerta': '%(asctime)s %(name)s[%(process)d]: [%(levelname)s] %(message)s [in %(pathname)s:%(lineno)d]',
            'flask': '%(asctime)s %(name)s[%(process)d]: [%(levelname)s] %(message)s',
            'request': '%(asctime)s %(name)s[%(process)d]: [%(levelname)s] %(message)s request_id=%(request_id)s ip=%(remote_addr)s',
            'urllib3': '%(asctime)s %(name)s[%(process)d]: [%(levelname)s] %(message)s',
            'werkzeug': '%(asctime)s %(name)s[%(process)d]: %(message)s'
        }
        self.default_formatter = logging.BASIC_FORMAT
        super().__init__()

    def format(self, record):

        fmt = record.name.split('.').pop(0)
        if flask.has_request_context():
            record.request_id = g.request_id if hasattr(g, 'request_id') else '-'
            record.endpoint = request.endpoint
            record.method = request.method
            record.url = request.url
            record.reqargs = request.args
            record.data = request.get_data(as_text=True)
            record.remote_addr = request.remote_addr
            record.user = g.login if hasattr(g, 'login') else None
            fmt = 'request'

        formatter = logging.Formatter(self.formatters.get(fmt, self.default_formatter))
        return formatter.format(record)


class JSONFormatter(logging.Formatter):

    RECORD_ATTRS = [
        'request_id', 'name', 'levelno', 'levelname', 'pathname', 'filename', 'module',
        'lineno', 'funcName', 'created', 'thread', 'threadName', 'process',  # 'message',
        'endpoint', 'method', 'url', 'reqargs', 'data', 'remote_addr', 'user'
    ]

    def format(self, record):
        payload = {
            attr: getattr(record, attr) for attr in self.RECORD_ATTRS if hasattr(record, attr)
        }
        payload['message'] = record.getMessage()

        # do not assume there's a Flask request context here so must use FLASK_ENV env var not app.debug
        indent = 2 if os.environ.get('FLASK_ENV', '') == 'development' else None
        return json.dumps(payload, indent=indent)
