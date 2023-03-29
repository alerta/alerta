import unittest

from alerta.app import create_app, db, plugins
from alerta.models.enums import Scope
from alerta.models.key import ApiKey


class AuthProxyTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'DEBUG': True,
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROXY': True,
            'AUTH_PROXY_ROLES_SEPARATOR': ';',
            'AUTH_PROXY_AUTO_SIGNUP': True
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.alert = {
            'event': 'Foo',
            'resource': 'Bar',
            'environment': 'Production',
            'service': ['Quux']
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='demo-key'
            )
            self.api_key.create()

        self.headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json'
        }

    def tearDown(self):
        plugins.plugins.clear()
        db.destroy()

    def test_401_error(self):

        response = self.client.get('/alerts')
        self.assertEqual(response.status_code, 401)

    def test_proxy_user(self):

        headers = {
            'X-Proxy-User': 'john1@doe.com',
            'X-Proxy-Roles': 'foo;user;bar'
        }

        response = self.client.get('/alerts', headers=headers)
        self.assertEqual(response.status_code, 200, response.data)

    def test_proxy_admin_user(self):

        headers = {
            'X-Proxy-User': 'b@admin.com',
            'X-Proxy-Roles': 'baz;admin;quux'
        }

        response = self.client.get('/users', headers=headers)
        self.assertEqual(response.status_code, 200, response.data)
