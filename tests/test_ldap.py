import unittest
import json

from alerta import create_app


def skip_ldap():
    try:
        import ldap  # noqa
    except ImportError:
        return True
    return False


class LdapAuthTestCase(unittest.TestCase):

    def setUp(self):

        if skip_ldap():
            self.skipTest('python-ldap import failed')
        # import alerta.auth.basic_ldap

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'AUTH_PROVIDER': 'ldap',
            'ADMIN_USERS': ['admin@alerta.io'],
            'ALLOWED_EMAIL_DOMAINS': ['bonaparte.fr', 'debeauharnais.fr', 'manorfarm.ru']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()


    def test_login(self):

        name = 'Josephine de Beauharnais'

        payload = {
            'username': 'foo',
            'password': 'jojo',
        }

        # sign-up user with no customer mapping
        response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 401)
