import uuid

from flask import Flask, g, request


class Tracing:

    def __init__(self, app=None) -> None:
        self.app = None
        if app:
            self.setup_tracing(app)

    def setup_tracing(self, app: Flask) -> None:
        app.before_request(self.get_request_id)
        app.after_request(self.set_request_id)

    @staticmethod
    def get_request_id():
        headers = request.headers
        request_id = (
            headers.get('X-Request-ID')
            or headers.get('X-Amzn-Trace-Id')
            or str(uuid.uuid4())
        )
        g.request_id = request_id

    @staticmethod
    def set_request_id(response):
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        return response
