import json
from datetime import datetime
from typing import Any, List
from uuid import uuid4

import blinker
import requests
from flask import Flask

from alerta.utils.format import CustomJSONEncoder

audit_signals = blinker.Namespace()

admin_audit_trail = audit_signals.signal('admin')
write_audit_trail = audit_signals.signal('write')
read_audit_trail = audit_signals.signal('read')  # not used
auth_audit_trail = audit_signals.signal('auth')


class AuditTrail:

    def __init__(self, app: Flask=None) -> None:
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        self.audit_url = app.config['AUDIT_URL']

        if 'admin' in app.config['AUDIT_TRAIL']:
            if app.config['AUDIT_LOG']:
                admin_audit_trail.connect(self.admin_log_response, app)
            if self.audit_url:
                admin_audit_trail.connect(self.admin_webhook_response, app)

        if 'write' in app.config['AUDIT_TRAIL']:
            if app.config['AUDIT_LOG']:
                write_audit_trail.connect(self.write_log_response, app)
            if self.audit_url:
                write_audit_trail.connect(self.write_webhook_response, app)

        if 'auth' in app.config['AUDIT_TRAIL']:
            if app.config['AUDIT_LOG']:
                auth_audit_trail.connect(self.auth_log_response, app)
            if self.audit_url:
                auth_audit_trail.connect(self.auth_webhook_response, app)

    def _log_response(self, app: Flask, category: str, event: str, message: str, user: str, customers: List[str],
                      scopes: List[str], resource_id: str, type: str, request: Any, **extra: Any) -> None:
        app.logger.info(self._fmt(category, event, message, user, customers,
                                  scopes, resource_id, type, request, **extra))

    def _webhook_response(self, app: Flask, category: str, event: str, message: str, user: str, customers: List[str],
                          scopes: List[str], resource_id: str, type: str, request: Any, **extra: Any) -> None:
        payload = self._fmt(category, event, message, user, customers, scopes, resource_id, type, request, **extra)
        try:
            requests.post(self.audit_url, data=payload, timeout=2)
        except Exception as e:
            app.logger.warning('Failed to send audit log entry to "{}" - {}'.format(self.audit_url, str(e)))

    def admin_log_response(self, app: Flask, **kwargs):
        self._log_response(app, 'admin', **kwargs)

    def admin_webhook_response(self, app: Flask, **kwargs):
        self._webhook_response(app, 'admin', **kwargs)

    def write_log_response(self, app: Flask, **kwargs):
        self._log_response(app, 'write', **kwargs)

    def write_webhook_response(self, app: Flask, **kwargs):
        self._webhook_response(app, 'write', **kwargs)

    def auth_log_response(self, app: Flask, **kwargs):
        self._log_response(app, 'auth', **kwargs)

    def auth_webhook_response(self, app: Flask, **kwargs):
        self._webhook_response(app, 'auth', **kwargs)

    @staticmethod
    def _fmt(category: str, event: str, message: str, user: str, customers: List[str], scopes: List[str],
             resource_id: str, type: str, request: Any, **extra: Any) -> str:
        return json.dumps({
            'id': str(uuid4()),
            '@timestamp': datetime.utcnow(),
            'event': event,
            'category': category,
            'message': message,
            'user': {
                'id': user,
                'customers': customers,
                'scopes': scopes
            },
            'resource': {
                'id': resource_id,
                'type': type
            },
            'request': {
                'endpoint': request.endpoint,
                'method': request.method,
                'url': request.url,
                'args': request.args.to_dict(),
                'data': request.get_data(as_text=True),
                'ipAddress': request.remote_addr
            },
            'extra': extra
        }, cls=CustomJSONEncoder)
