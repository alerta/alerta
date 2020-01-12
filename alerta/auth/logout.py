from flask import current_app, jsonify
from flask_cors import cross_origin

from . import auth


@auth.route('/auth/logout', methods=['OPTIONS', 'GET', 'POST'])
@cross_origin(supports_credentials=True)
def logout():

    if not current_app.config['OIDC_LOGOUT_URL']:
        return jsonify(status='ok', message='OIDC end_session_endpoint not configured')

    return jsonify(status='ok', logoutUrl=current_app.config['OIDC_LOGOUT_URL'])
