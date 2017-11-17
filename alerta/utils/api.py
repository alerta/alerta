
import logging

from functools import wraps
from os.path import join as path_join

from flask import current_app, request

from alerta.app import plugins
from alerta.exceptions import ApiError
from alerta.exceptions import RejectException, RateLimit, BlackoutPeriod

try:
    from urllib.parse import urljoin, urlparse, urlunparse
except ImportError:
    from urlparse import urljoin, urlparse, urlunparse


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


def absolute_url(path=''):
    # ensure that "path" (see urlparse result) part of url has both leading and trailing slashes
    conf_base_url = urlunparse([(x if i != 2 else path_join('/', x, '')) for i, x in enumerate(urlparse(current_app.config.get('BASE_URL', '/')))])
    try:
        base_url = urljoin(request.base_url, conf_base_url)
    except RuntimeError:  # Working outside of request context
        base_url = conf_base_url
    return urljoin(base_url, path.lstrip('/'))


def add_remote_ip(req, alert):
    if req.headers.getlist("X-Forwarded-For"):
        alert.attributes.update(ip=req.headers.getlist("X-Forwarded-For")[0])
    else:
        alert.attributes.update(ip=req.remote_addr)


def process_alert(alert):

    for plugin in plugins.routing(alert):
        try:
            alert = plugin.pre_receive(alert)
        except (RejectException, BlackoutPeriod, RateLimit):
            raise
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise RuntimeError("Error while running pre-receive plug-in '%s': %s" % (plugin.name, str(e)))
            else:
                logging.error("Error while running pre-receive plug-in '%s': %s" % (plugin.name, str(e)))
        if not alert:
            raise SyntaxError("Plug-in '%s' pre-receive hook did not return modified alert" % plugin.name)

    try:
        if alert.is_duplicate():
            alert = alert.deduplicate()
        elif alert.is_correlated():
            alert = alert.update()
        else:
            alert = alert.create()
    except Exception as e:
        raise ApiError(str(e))

    updated = None
    for plugin in plugins.routing(alert):
        try:
            updated = plugin.post_receive(alert)
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise ApiError("Error while running post-receive plug-in '%s': %s" % (plugin.name, str(e)))
            else:
                logging.error("Error while running post-receive plug-in '%s': %s" % (plugin.name, str(e)))
        if updated:
            alert = updated

    if updated:
        alert.tag(alert.tags)
        alert.update_attributes(alert.attributes)

    return alert


def process_status(alert, status, text):

    updated = None
    for plugin in plugins.routing(alert):
        try:
            updated = plugin.status_change(alert, status, text)
        except RejectException:
            raise
        except Exception as e:
            if current_app.config['PLUGINS_RAISE_ON_ERROR']:
                raise ApiError("Error while running status plug-in '%s': %s" % (plugin.name, str(e)))
            else:
                logging.error("Error while running status plug-in '%s': %s" % (plugin.name, str(e)))
        if updated:
            try:
                alert, status, text = updated
            except Exception:
                alert = updated

    if updated:
        alert.tag(alert.tags)
        alert.update_attributes(alert.attributes)

    return alert, status, text


def deepmerge(first, second):
    result = {}
    for key in first.keys():
        if key in second:
            if isinstance(first[key], dict) and isinstance(second[key], dict):
                result[key] = deepmerge(first[key], second[key])
            else:
                result[key] = second[key]
        else:
            result[key] = first[key]
    for key, value in second.items():
        if key not in first:  # already processed above
            result[key] = value
    return result
