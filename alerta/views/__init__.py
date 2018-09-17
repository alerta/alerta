
from flask import Blueprint, request, jsonify, current_app

from alerta.exceptions import ApiError
from alerta.utils.api import absolute_url

api = Blueprint('api', __name__)

from . import alerts, blackouts, customers, heartbeats, keys, permissions, users, oembed  # noqa


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
    return jsonify(status='ok', uri=absolute_url(), data={'description': 'Alerta API'}, links=sorted(links, key=lambda k: k['href']))


@api.route('/_', methods=['GET'])
def debug():
    return 'OK'


@api.route('/config', methods=['GET'])
def config():
    return jsonify({
        'endpoint': absolute_url().rstrip('/'),  # FIXME - shouldn't need to rstrip()
        'auth_required': current_app.config['AUTH_REQUIRED'],
        'customer_views': current_app.config['CUSTOMER_VIEWS'],
        'provider': current_app.config['AUTH_PROVIDER'],
        'signup_enabled': current_app.config['SIGNUP_ENABLED'],
        'client_id': current_app.config['OAUTH2_CLIENT_ID'],
        'github_url': current_app.config['GITHUB_URL'],
        'gitlab_url': current_app.config['GITLAB_URL'],
        'keycloak_url': current_app.config['KEYCLOAK_URL'],
        'keycloak_realm': current_app.config['KEYCLOAK_REALM'],
        'pingfederate_url': current_app.config['PINGFEDERATE_URL'],
        'colors': current_app.config['COLOR_MAP'],
        'severity': current_app.config['SEVERITY_MAP'],
        'dates': {
            'shortTime': 'shortTime',  # 1:39 PM
            'mediumDate': 'medium',  # Apr 26, 2016 1:39:44 PM
            'longDate': 'EEEE, MMMM d, yyyy h:mm:ss.sss a (Z)'  # Tuesday, April 26, 2016 1:39:43.987 PM (+0100)
        },
        'audio': {},  # not supported yet
        'tracking_id': current_app.config['GOOGLE_TRACKING_ID'],
        'refresh_interval': current_app.config['AUTO_REFRESH_INTERVAL']
    })
