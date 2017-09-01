
from flask import Blueprint, request, jsonify, current_app, g

from alerta.app import db
from alerta.app.utils.api import absolute_url
from alerta.app.exceptions import ApiError

api = Blueprint('api', __name__)

from . import alerts, blackouts, customers, heartbeats, keys, permissions, users, oembed


@api.before_request
def before_request():
    if request.method in ['POST', 'PUT'] and not request.is_json:
        raise ApiError("POST and PUT requests must set 'Content-type' to 'application/json'", 415)


@api.route('/', methods=['OPTIONS', 'GET'])
def index():
    links = []
    for rule in current_app.url_map.iter_rules():
        links.append({
            "rel": rule.endpoint,
            "href": absolute_url(rule.rule),
            "method": ','.join([m for m in rule.methods if m not in ['HEAD', 'OPTIONS']])
        })
    return jsonify(status="ok", uri=absolute_url(), data={'description':'Alerta API'}, links=sorted(links, key=lambda k: k["href"]))


@api.route('/_', methods=['GET'])
def debug():
    return jsonify(db=db.version)



