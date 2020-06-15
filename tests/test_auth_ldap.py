import json
import unittest
from unittest.mock import patch

import ldap

from alerta.app import create_app, db
from alerta.models.enums import Scope
from alerta.models.key import ApiKey


class AuthLdapTestCase(unittest.TestCase):

    class LDAPObjectMock:
        def __init__(self, user_to_login, pass_to_login, user_to_bind, pass_to_bind, search_results):
            self.user_to_login = user_to_login
            self.pass_to_login = pass_to_login
            self.user_to_bind = user_to_bind
            self.pass_to_bind = pass_to_bind
            self.search_results = search_results

        def simple_bind_s(self, who=None, cred=None, serverctrls=None, clientctrls=None):
            # raise Exception("{}-{}......{}-{}".format(who, cred, self.user_to_bind, self.pass_to_bind))
            if not((who == self.user_to_login and cred == self.pass_to_login)
                   or (who == self.user_to_bind and cred == self.pass_to_bind)):
                raise ldap.INVALID_CREDENTIALS
            pass

        def search_s(self, base, scope, filterstr=None, attrlist=None, attrsonly=0):
            return self.search_results

    def setUp(self):

        test_config = {
            'TESTING': True,
            'DEBUG': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'ldap',
            'CUSTOMER_VIEWS': True,
            'ADMIN_USERS': ['admin@alerta.io'],
            'LDAP_URL': 'ldap://myldap.server',
            'LDAP_BIND_USERNAME': 'user_to_bind',
            'LDAP_BIND_PASSWORD': 'password_to_bind',
            'LDAP_DOMAINS_SEARCH_QUERY': {
                'debeauharnais.fr': 'sAMAccountName={username}'
            },
            'LDAP_DOMAINS_USER_BASEDN': {
                'debeauharnais.fr': ''
            },
            'LDAP_DOMAINS': {
                'debeauharnais.fr': 'DN=%s'
            }
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

    def tearDown(self):
        db.destroy()

    def test_401_error(self):

        response = self.client.get('/alerts')
        self.assertEqual(response.status_code, 401)

    def test_ldap_login_defined_dn(self):

        # Attemps to login with the defined DN instead of performing a search
        self.app.config['LDAP_DOMAINS_SEARCH_QUERY'] = {}

        mock_ldap = AuthLdapTestCase.LDAPObjectMock(
            'DN=josephine',
            'jojo',
            'user_to_bind',
            'password_to_bind',
            [('DN=josephine', {'mail': [bytearray('josephine@debeauharnais.fr', 'utf-8')]})]
        )

        data = self.login_test(mock_ldap, 200)
        self.assertIn('token', data)

    def test_ldap_login_search(self):

        mock_ldap = AuthLdapTestCase.LDAPObjectMock(
            'DN=josephine',
            'jojo',
            'user_to_bind',
            'password_to_bind',
            [('DN=josephine', {'mail': [bytearray('josephine@debeauharnais.fr', 'utf-8')]})]
        )

        data = self.login_test(mock_ldap, 200)
        self.assertIn('token', data)

    def test_ldap_login_wrong_password(self):

        mock_ldap = AuthLdapTestCase.LDAPObjectMock(
            'DN=josephine',
            'jojo_wrong',
            'user_to_bind',
            'password_to_bind',
            [('DN=josephine', {'mail': [bytearray('josephine@debeauharnais.fr', 'utf-8')]})]
        )

        data = self.login_test(mock_ldap, 401)
        self.assertIn('message', data)
        self.assertEqual('invalid username or password', data.get('message'))

    def test_ldap_login_wrong_bind_password(self):

        mock_ldap = AuthLdapTestCase.LDAPObjectMock(
            'DN=josephine',
            'jojo',
            'user_to_bind',
            'password_to_bind_wrong',
            [('DN=josephine', {'mail': [bytearray('josephine@debeauharnais.fr', 'utf-8')]})]
        )

        data = self.login_test(mock_ldap, 401)
        self.assertIn('message', data)
        self.assertEqual('invalid ldap bind username or password', data.get('message'))

    def login_test(self, mock_ldap, expected_response_code):
        # add customer mapping
        payload = {
            'customer': 'Bonaparte Industries',
            'match': 'debeauharnais.fr'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)
        json.loads(response.data.decode('utf-8'))

        payload = {
            'email': 'josephine@debeauharnais.fr',
            'password': 'jojo'
        }

        # login now that customer mapping exists
        with patch('ldap.initialize', return_value=mock_ldap):
            response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
            self.assertEqual(response.status_code, expected_response_code)

        return json.loads(response.data.decode('utf-8'))
