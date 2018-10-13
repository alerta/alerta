
from alerta.app import alarm_model
from alerta.exceptions import ApiError
from alerta.utils.response import absolute_url
from flask import Blueprint, request, jsonify, current_app

api = Blueprint('api', __name__)

from . import alerts, blackouts, customers, heartbeats, keys, permissions, users, oembed  # noqa

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
    return jsonify(status='ok', uri=absolute_url(), data={'description': 'Alerta API'}, links=sorted(links, key=lambda k: k['href']))


@api.route('/_', methods=['GET'])
def debug():
    return 'OK'


@api.route('/config', methods=['GET'])
def config():
    return jsonify({
        'endpoint': absolute_url().rstrip('/'),  # FIXME - shouldn't need to rstrip()
        'alarm_model': {
            'name': alarm_model.name
        },
        'auth_required': current_app.config['AUTH_REQUIRED'],
        'provider': current_app.config['AUTH_PROVIDER'],
        'customer_views': current_app.config['CUSTOMER_VIEWS'],
        'signup_enabled': current_app.config['SIGNUP_ENABLED'],
        'client_id': current_app.config['OAUTH2_CLIENT_ID'],
        'github_url': current_app.config['GITHUB_URL'],
        'gitlab_url': current_app.config['GITLAB_URL'],
        'keycloak_url': current_app.config['KEYCLOAK_URL'],
        'keycloak_realm': current_app.config['KEYCLOAK_REALM'],
        'pingfederate_url': current_app.config['PINGFEDERATE_URL'],
        'site_logo_url': current_app.config['SITE_LOGO_URL'],
        'severity': alarm_model.Severity,
        'colors': alarm_model.Colors,
        'dates': {
            'shortTime': current_app.config['DATE_FORMAT_SHORT_TIME'],
            'mediumDate': current_app.config['DATE_FORMAT_MEDIUM_DATE'],
            'longDate': current_app.config['DATE_FORMAT_LONG_DATE']
        },
        'audio': {
            'new': current_app.config['DEFAULT_AUDIO_FILE']
        },
        'columns': current_app.config['COLUMNS'],
        'sort_by': current_app.config['SORT_LIST_BY'],
        'actions': current_app.config['ACTIONS'],
        'tracking_id': current_app.config['GOOGLE_TRACKING_ID'],
        'refresh_interval': current_app.config['AUTO_REFRESH_INTERVAL']
    })
