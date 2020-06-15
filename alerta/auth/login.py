from flask import current_app
from flask_cors import cross_origin

from . import auth


@auth.route('/auth/login', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def login():
    if current_app.config['AUTH_PROVIDER'] == 'ldap':
        from . import basic_ldap
        return basic_ldap.login()
    else:
        from . import basic
        return basic.login()
