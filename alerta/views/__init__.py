from flask import Blueprint, current_app, jsonify, request

from alerta.app import custom_webhooks
from alerta.exceptions import ApiError
from alerta.utils.response import absolute_url

api = Blueprint('api', __name__)

from . import alerts, blackouts, config, customers, groups, heartbeats, keys, oembed, permissions, users  # noqa isort:skip

try:
    from . import bulk  # noqa
except ImportError:
    pass


@api.before_request
def before_request():
    if request.method in ['POST', 'PUT'] and not request.is_json:
        raise ApiError("POST and PUT requests must set 'Content-type' to 'application/json'", 415)


@api.route('/', methods=['OPTIONS', 'GET'])
def index():
    links = []

    for rule in current_app.url_map.iter_rules():
        links.append({
            'rel': rule.endpoint,
            'href': absolute_url(rule.rule),
            'method': ','.join([m for m in rule.methods if m not in ['HEAD', 'OPTIONS']])
        })

    for rule in custom_webhooks.iter_rules():
        links.append({
            'rel': rule.endpoint,
            'href': absolute_url(rule.rule),
            'method': ','.join(rule.methods)
        })

    return jsonify(status='ok', uri=absolute_url(), data={'description': 'Alerta API'}, links=sorted(links, key=lambda k: k['href']))


@api.route('/_', methods=['GET'])
def debug():
    return 'OK'
