from functools import wraps
from urllib.parse import urljoin

from flask import current_app, request


def jsonp(func):
    """Wraps JSONified output for JSONP requests."""
    @wraps(func)
    def decorated(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            data = str(func(*args, **kwargs).data)
            content = str(callback) + '(' + data + ')'
            mimetype = 'application/javascript'
            return current_app.response_class(content, mimetype=mimetype)
        else:
            return func(*args, **kwargs)
    return decorated


def absolute_url(path: str = '') -> str:
    try:
        base_url = current_app.config['BASE_URL'] or request.url_root
    except Exception:
        base_url = '/'
    return urljoin(base_url + '/', path.lstrip('/')) if path else base_url


def base_url():
    return absolute_url(path='')
