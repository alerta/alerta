from flask_cors import cross_origin

from alerta.app import providers

from . import auth


@auth.route('/auth/login', methods=['OPTIONS', 'POST'])
@cross_origin(supports_credentials=True)
def login():
    if providers.has_provider('ldap'):
        from . import basic_ldap
        return basic_ldap.login()
    else:
        from . import basic
        return basic.login()
