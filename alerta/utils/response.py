from functools import wraps
from os.path import join as path_join
from urllib.parse import urljoin, urlparse, urlunparse

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


def absolute_url(path: str='') -> str:
    # ensure that "path" (see urlparse result) part of url has both leading and trailing slashes
    conf_base_url = urlunparse([(x if i != 2 else path_join('/', x, ''))
                                for i, x in enumerate(urlparse(current_app.config.get('BASE_URL', '/')))])
    try:
        base_url = urljoin(request.base_url, conf_base_url)
    except RuntimeError:  # Working outside of request context
        base_url = conf_base_url
    return urljoin(base_url, path.lstrip('/'))
