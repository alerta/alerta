
import traceback

from flask import Response, current_app, jsonify


class AlertaException(IOError):
    pass


class RejectException(AlertaException):
    """The alert was rejected because the format did not meet the required policy."""
    pass


class RateLimit(AlertaException):
    """Too many alerts have been received for a resource or from an origin."""
    pass


class BlackoutPeriod(AlertaException):
    """Alert was not processed because it was sent during a blackout period."""
    pass


class NoCustomerMatch(AlertaException):
    """There was no customer lookup found for the user or group."""
    pass


class BaseError(Exception):
    code = 500

    def __init__(self, message, code=None, errors=None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.errors = errors


class ApiError(BaseError):
    pass


class BasicAuthError(BaseError):
    pass


class ExceptionHandlers:

    def register(self, app):
        from werkzeug.exceptions import default_exceptions
        for code in default_exceptions.keys():
            app.register_error_handler(code, handle_http_error)
        app.register_error_handler(ApiError, handle_api_error)
        app.register_error_handler(BasicAuthError, handle_basic_auth_error)
        app.register_error_handler(Exception, handle_exception)


def handle_http_error(error):
    if error.code >= 500:
        current_app.logger.exception(error)
    return jsonify({
        'status': 'error',
        'message': str(error),
        'code': error.code,
        'errors': [
            error.description
        ]
    }), error.code


def handle_api_error(error):
    if error.code >= 500:
        current_app.logger.exception(error)
    return jsonify({
        'status': 'error',
        'message': error.message,
        'code':  error.code,
        'errors': error.errors
    }), error.code


def handle_basic_auth_error(error):
    return jsonify({
        'status': 'error',
        'message': error.message,
        'code':  error.code,
        'errors': error.errors
    }), error.code, {'WWW-Authenticate': 'Basic realm=%s' % current_app.config['BASIC_AUTH_REALM']}


def handle_exception(error):
    current_app.logger.exception(error)
    return jsonify({
        'status': 'error',
        'message': str(error),
        'code': 500,
        'errors': [
            traceback.format_exc()
        ]
    }), 500
