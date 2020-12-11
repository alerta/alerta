from flask import current_app, jsonify

from alerta.app import alarm_model
from alerta.utils.response import absolute_url

from . import api


@api.route('/config', methods=['GET'])
def config():
    return jsonify({
        'debug': current_app.debug,
        'endpoint': absolute_url().rstrip('/'),  # FIXME - shouldn't need to rstrip()
        'alarm_model': {
            'name': alarm_model.name,
            'severity': alarm_model.Severity,
            'colors': alarm_model.Colors,
            'status': alarm_model.Status,
            'defaults': {
                'status': alarm_model.DEFAULT_STATUS,
                'normal_severity': alarm_model.DEFAULT_NORMAL_SEVERITY,
                'previous_severity': alarm_model.DEFAULT_PREVIOUS_SEVERITY
            }
        },
        'auth_required': current_app.config['AUTH_REQUIRED'],
        'provider': current_app.config['AUTH_PROVIDER'],
        'customer_views': current_app.config['CUSTOMER_VIEWS'],
        'signup_enabled': current_app.config['SIGNUP_ENABLED'] if current_app.config['AUTH_PROVIDER'] == 'basic' else False,
        'email_verification': current_app.config['EMAIL_VERIFICATION'],
        'client_id': current_app.config['OAUTH2_CLIENT_ID'],
        'azure_tenant': current_app.config['AZURE_TENANT'],
        'aws_region': current_app.config['AWS_REGION'],
        'cognito_domain': current_app.config['COGNITO_DOMAIN'],
        'github_url': current_app.config['GITHUB_URL'],
        'gitlab_url': current_app.config['GITLAB_URL'],
        'keycloak_url': current_app.config['KEYCLOAK_URL'],
        'keycloak_realm': current_app.config['KEYCLOAK_REALM'],
        'oidc_auth_url': current_app.config['OIDC_AUTH_URL'],
        'site_logo_url': current_app.config['SITE_LOGO_URL'],
        'severity': alarm_model.Severity,  # FIXME - moved to alarm model
        'colors': alarm_model.Colors,  # FIXME - moved to alarm model
        'timeouts': {
            'alert': current_app.config['ALERT_TIMEOUT'],
            'heartbeat': current_app.config['HEARTBEAT_TIMEOUT'],
            'ack': current_app.config['ACK_TIMEOUT'],
            'shelve': current_app.config['SHELVE_TIMEOUT']
        },
        'dates': {
            'shortTime': current_app.config['DATE_FORMAT_SHORT_TIME'],
            'mediumDate': current_app.config['DATE_FORMAT_MEDIUM_DATE'],
            'longDate': current_app.config['DATE_FORMAT_LONG_DATE']
        },
        'font': current_app.config['DEFAULT_FONT'],
        'audio': {
            'new': current_app.config['DEFAULT_AUDIO_FILE']
        },
        'columns': current_app.config['COLUMNS'],
        'sort_by': current_app.config['SORT_LIST_BY'],
        'filter': current_app.config['DEFAULT_FILTER'],
        'indicators': {
            'severity': current_app.config['ASI_SEVERITY'],
            'queries': current_app.config['ASI_QUERIES']
        },
        'actions': current_app.config['ACTIONS'],
        'tracking_id': current_app.config['GOOGLE_TRACKING_ID'],
        'refresh_interval': current_app.config['AUTO_REFRESH_INTERVAL'],
        'environments': current_app.config['ALLOWED_ENVIRONMENTS']
    })
