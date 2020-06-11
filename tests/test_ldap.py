import unittest
from unittest import mock
import json

from alerta import create_app


def skip_ldap():
    try:
        import ldap  # noqa
    except ImportError:
        return True
    return False


class LdapAuthTestCase(unittest.TestCase):

    class LDAPObjectMock:
        def __init__(self, user_to_login, pass_to_login, user_to_bind, pass_to_bind, search_results):
            print('ldap mock init')
            self.user_to_login = user_to_login
            self.pass_to_login = pass_to_login
            self.user_to_bind = user_to_bind
            self.pass_to_bind = pass_to_bind
            self.search_results = search_results

        def simple_bind_s(self, who=None, cred=None, serverctrls=None, clientctrls=None):
            print('******** simple bind')
            print(who)
            print(cred)
            # raise Exception("{}-{}......{}-{}".format(who, cred, self.user_to_bind, self.pass_to_bind))
            if not((who == self.user_to_login and cred == self.pass_to_login)
                   or (who == self.user_to_bind and cred == self.pass_to_bind)):
                import ldap
                raise ldap.INVALID_CREDENTIALS
            pass

        def search_s(self, base, scope, filterstr=None, attrlist=None, attrsonly=0):
            return self.search_results

    def setUp(self):

        if skip_ldap():
            self.skipTest('python-ldap import failed')

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'ldap',
            'ADMIN_USERS': ['admin@alerta.io'],
            'ALLOWED_EMAIL_DOMAINS': ['bonaparte.fr', 'debeauharnais.fr', 'manorfarm.ru'],
            'LDAP_DOMAINS': {
                'debeauharnais.fr': 'DN=%s'
            }
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

    def test_login(self):

        mock_ldap = LdapAuthTestCase.LDAPObjectMock(
            'DN=josephine',
            'jojo',
            'user_to_bind',
            'password_to_bind',
            [('DN=josephine', {'mail': [bytearray('josephine@debeauharnais.fr', 'utf-8')]})]
        )

        payload = {
            'username': 'josephine@debeauharnais.fr',
            'password': 'jojo',
        }

        with mock.patch('ldap.initialize', return_value=mock_ldap):
            response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
            self.assertEqual(response.status_code, 200)
