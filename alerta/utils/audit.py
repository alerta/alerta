import json
from datetime import datetime
from typing import Any, List
from uuid import uuid4

import blinker
import requests
from flask import Flask

from alerta.utils.format import CustomJSONEncoder

audit_signals = blinker.Namespace()

audit_trail = audit_signals.signal('audit')


class AuditTrail:

    def __init__(self, app: Flask=None) -> None:
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        if app.config['AUDIT_LOG']:
            audit_trail.connect(self.log_response, app)

        self.audit_url = app.config['AUDIT_URL']
        if self.audit_url:
            audit_trail.connect(self.webhook_response, app)

    def log_response(self, app: Flask, event: str, message: str, user: str, customers: List[str],
                     scopes: List[str], resource_id: str, type: str, request: Any, **extra: Any) -> None:
        app.logger.debug(self._fmt(event, message, user, customers, scopes, resource_id, type, request, **extra))

    def webhook_response(self, app: Flask, event: str, message: str, user: str, customers: List[str],
                         scopes: List[str], resource_id: str, type: str, request: Any, **extra: Any) -> None:
        payload = self._fmt(event, message, user, customers, scopes, resource_id, type, request, **extra)
        try:
            requests.post(self.audit_url, data=payload, timeout=2)
        except Exception as e:
            app.logger.warning('Failed to send audit log entry to "{}" - {}'.format(self.audit_url, str(e)))

    @staticmethod
    def _fmt(event: str, message: str, user: str, customers: List[str], scopes: List[str],
             resource_id: str, type: str, request: Any, **extra: Any) -> str:
        return json.dumps({
            'id': str(uuid4()),
            '@timestamp': datetime.utcnow(),
            'event': event,
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
