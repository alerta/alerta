import json
import logging
import os
from logging.config import dictConfig

import flask
import yaml
from flask import Flask, current_app, g, request


class Logger:

    def __init__(self, app: Flask = None) -> None:
        self.app = None
        if app:
            self.setup_logging(app)

    def setup_logging(self, app: Flask) -> None:

        def open_file(filename, mode='r'):
            path = os.path.join(os.path.dirname(__file__), filename)
            return open(path, mode)

        log_config_file = os.path.expandvars(os.path.expanduser(app.config['LOG_CONFIG_FILE']))
        log_level = 'DEBUG' if app.debug else app.config['LOG_LEVEL']

        if os.path.exists(log_config_file):
            with open_file(log_config_file) as f:
                dictConfig(yaml.safe_load(f.read()))
        else:
            if app.config['LOG_FORMAT'] in ['default', 'simple', 'verbose', 'json', 'syslog']:
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
                'disable_existing_loggers': True,
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
                    'syslog': {
                        '()': 'alerta.utils.logging.SyslogFormatter',
                        'facility': app.config['LOG_FACILITY']
                    },
                    'custom': {
                        'format': custom_format
                    }
                },
                'filters': {
                    'requests': {
                        '()': 'alerta.utils.logging.RequestFilter',
                        'methods': app.config['LOG_METHODS']
                    },
                    'context': {
                        '()': 'alerta.utils.logging.ContextFilter',
                    }
                },
                'handlers': {
                    'console': {
                        'class': 'logging.StreamHandler',
                        'formatter': log_format,
                        'level': log_level,
                        'filters': ['context', 'requests'],
                        'stream': 'ext://sys.stdout'
                    },
                    'file': {
                        'class': 'logging.handlers.RotatingFileHandler',
                        'formatter': log_format,
                        'level': log_level,
                        'filters': ['context', 'requests'],
                        'filename': log_file,
                        'maxBytes': app.config['LOG_MAX_BYTES'],
                        'backupCount': app.config['LOG_BACKUP_COUNT']
                    },
                    'wsgi': {
                        'class': 'logging.StreamHandler',
                        'formatter': log_format,
                        'filters': ['context', 'requests'],
                        'stream': 'ext://flask.logging.wsgi_errors_stream'
                    }
                },
                'loggers': {
                    'alerta': {
                        'level': log_level,
                    },
                    'flask_cors.core': {
                        'level': 'WARNING',
                    },
                    'mohawk': {
                        'level': log_level,
                    },
                    'requests': {
                        'level': log_level,
                    },
                    'urllib3': {
                        'level': log_level,
                    },
                    'werkzeug': {
                        'level': 'WARNING',
                    },
                },
                'root': {
                    'level': log_level,
                    'handlers': app.config['LOG_HANDLERS'],
                },
            })

            # from logging_tree import printout
            # printout()

            app.after_request(self.log_response)

    @staticmethod
    def log_response(response):
        request_protocol = request.environ['SERVER_PROTOCOL']
        current_app.logger.info(f'"{request.method} {request.path} {request_protocol}" {response.status_code} {response.content_length}')
        return response


class RequestFilter(logging.Filter):

    def __init__(self, methods=None):
        self.methods = methods or []
        super().__init__()

    def filter(self, record):

        if hasattr(record, 'method'):
            if record.method == '-' or record.method in self.methods:
                return True
        else:
            return True


class ContextFilter(logging.Filter):

    def filter(self, record):

        if flask.has_request_context():
            record.request_id = g.request_id if hasattr(g, 'request_id') else '-'
            record.endpoint = request.endpoint
            record.method = request.method
            record.url = request.url
            record.reqargs = request.args
            record.data = request.get_data(as_text=True)
            record.remote_addr = request.remote_addr
            record.user = g.login if hasattr(g, 'login') else None
        else:
            record.request_id = '-'
            record.endpoint = '-'
            record.method = '-'
            record.url = '-'
            record.reqargs = '-'
            record.data = '-'
            record.remote_addr = '-'
            record.user = '-'

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


class SyslogFormatter(logging.Formatter):

    def __init__(self, facility='local0'):

        self.facility = facility
        super().__init__()

    def format(self, record):

        import platform

        #           Numerical             Facility
        #              Code
        #
        #               0             kernel messages
        #               1             user-level messages
        #               2             mail system
        #               3             system daemons
        #               4             security/authorization messages
        #               5             messages generated internally by syslogd
        #               6             line printer subsystem
        #               7             network news subsystem
        #               8             UUCP subsystem
        #               9             clock daemon
        #              10             security/authorization messages
        #              11             FTP daemon
        #              12             NTP subsystem
        #              13             log audit
        #              14             log alert
        #              15             clock daemon (note 2)
        #              16             local use 0  (local0)
        #              17             local use 1  (local1)
        #              18             local use 2  (local2)
        #              19             local use 3  (local3)
        #              20             local use 4  (local4)
        #              21             local use 5  (local5)
        #              22             local use 6  (local6)
        #              23             local use 7  (local7)

        syslog_facility = {
            'kern': 0,
            'user': 1,
            'mail': 2,
            'daemon': 3,
            'auth': 4,
            'syslog': 5,
            'lpr': 6,
            'news': 7,
            'uucp': 8,
            'cron': 9,
            'authpriv': 10,
            'ftp': 11,
            'ntp': 12,
            'security': 13,
            'audit': 13,
            'console': 14,
            'alert': 14,
            'clock': 15,
            'local0': 16,
            'local1': 17,
            'local2': 18,
            'local3': 19,
            'local4': 20,
            'local5': 21,
            'local6': 22,
            'local7': 23,
        }

        #               0       Emergency: system is unusable
        #               1       Alert: action must be taken immediately
        #               2       Critical: critical conditions
        #               3       Error: error conditions
        #               4       Warning: warning conditions
        #               5       Notice: normal but significant condition
        #               6       Informational: informational messages
        #               7       Debug: debug-level messages

        syslog_severity = {
            'CRITICAL': {'severity': 'Critical', 'code': 2},
            'FATAL': {'severity': 'Critical', 'code': 2},
            'ERROR': {'severity': 'Error', 'code': 3},
            'WARN': {'severity': 'Warning', 'code': 4},
            'WARNING': {'severity': 'Warning', 'code': 4},
            'INFO': {'severity': 'Informational', 'code': 6},
            'DEBUG': {'severity': 'Debug', 'code': 7},
        }

        record.PRI = syslog_facility[self.facility] * 8 + syslog_severity[record.levelname]['code']
        record.VERSION = '1'
        record.HOSTNAME = platform.node()
        record.APP_NAME = record.name
        record.PROCID = record.process
        record.MSGID = record.funcName

        if flask.has_request_context():
            record.ip = request.remote_addr
            record.request_id = g.request_id if hasattr(g, 'request_id') else '-'
        else:
            record.ip = '-'
            record.request_id = '-'

        formatter = logging.Formatter(
            fmt='<%(PRI)d>%(VERSION)s %(asctime)s %(HOSTNAME)s %(APP_NAME)s %(PROCID)s %(MSGID)s'
                ' [origin ip="%(ip)s"]'
                ' [request@52926 requestId="%(request_id)s"]'
                ' [file@52926 filename="%(pathname)s" lineno="%(lineno)d"]'
                ' %(levelname)s: %(msg)s',
            datefmt='%Y-%m-%dT%H:%M:%SZ'
        )
        return formatter.format(record)
