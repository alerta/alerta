import json
import unittest

from alerta.app import create_app, db
from alerta.models.enums import Scope
from alerta.models.key import ApiKey


def skip_ldap():
    try:
        import ldap  # noqa
    except ImportError:
        return True
    return False


class LdapAuthTestCase(unittest.TestCase):

    def setUp(self):

        if skip_ldap():
            self.skipTest('ldap import failed')

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'ADMIN_USERS': ['admin@alerta.io'],
            'AUTH_PROVIDER': 'ldap',
            'LDAP_URL': 'ldap://openldap:389',
            'LDAP_DOMAINS': {
                'my-domain.com': 'cn=%s,dc=my-domain,dc=com'
            },
            # 'ALLOWED_EMAIL_DOMAINS': ['bonaparte.fr', 'debeauharnais.fr', 'manorfarm.ru']
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
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

    def tearDown(self):
        db.destroy()

    def test_no_signup(self):

        response = self.client.post('/auth/signup', content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_login(self):

        name = 'Josephine de Beauharnais'

        payload = {
            'name': name,
            'email': 'josephine@debeauharnais.fr',
            'password': 'jojo',
            'text': 'Test login'
        }

        # sign-up user with no customer mapping
        response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 403)

        # add customer mapping
        payload = {
            'customer': 'Bonaparte Industries',
            'match': 'debeauharnais.fr'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        customer_id = data['id']

        payload = {
            'email': 'josephine@debeauharnais.fr',
            'password': 'jojo'
        }

        # login now that customer mapping exists
        response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
        # self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('token', data)

        token = data['token']

        headers = {
            'Authorization': 'Bearer ' + token,
            'Content-type': 'application/json'
        }

        # create a customer demo key
        payload = {
            'user': 'customer-demo-key-user',
            'type': 'read-only'
        }

        response = self.client.post('/key', data=json.dumps(payload), content_type='application/json', headers=headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-only key')

        customer_api_key = data['key']

        response = self.client.get('/alerts', headers={'Authorization': 'Key ' + customer_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('total', data)

        response = self.client.get('/key/' + customer_api_key, headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['key']['scopes'], ['read'])

        response = self.client.delete('/key/' + customer_api_key, headers={'Authorization': 'Key ' + customer_api_key})
        self.assertEqual(response.status_code, 403)

        response = self.client.delete('/key/' + customer_api_key, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # get user
        response = self.client.get('/users', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(name, [u['name'] for u in data['users']])

        user_id = [u['id'] for u in data['users'] if u['name'] == name][0]

        # delete user
        response = self.client.delete('/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # delete customer mapping
        response = self.client.delete('/customer/' + customer_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
