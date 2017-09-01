
from flask import jsonify


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


class ApiError(Exception):
    code = 500

    def __init__(self, message, code=None):
        super(ApiError, self).__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class ExceptionHandlers(object):

    def register(self, app):
        from werkzeug.exceptions import default_exceptions
        for code in default_exceptions.keys():
            app.register_error_handler(code, handle_http_error)
        app.register_error_handler(ApiError, handle_api_error)
        app.register_error_handler(Exception, handle_exception)


def handle_api_error(error):
    return jsonify({
        'status': 'error',
        'message': error.message,
        'code':  error.code
    }), error.code


def handle_http_error(error):
    return jsonify({
        'status': 'error',
        'message': '%s: %s' % (error.name, error.description),
        'code': error.code
    }), error.code


def handle_exception(error):
    return jsonify({
        'status': 'error',
        'message': str(error),
        'code': 500
    }), 500
