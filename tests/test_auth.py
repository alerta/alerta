
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from alerta.app import create_app, db
from alerta.app.models.key import ApiKey
from alerta.app.models.token import Jwt


class AuthTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'ADMIN_USERS': ['admin@alerta.io'],
            'ALLOWED_EMAIL_DOMAINS': ['bonaparte.fr', 'debeauharnais.fr']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.alert = {
            'event': 'Foo',
            'resource': 'Bar',
            'environment': 'Production',
            'service': ['Quux']
        }

        with self.app.app_context():
            self.api_key = db.create_key(
                ApiKey.parse(
                    {
                        "user": "admin@alerta.io",
                        "type": "read-write",
                        "text": "demo-key"
                    }
                )
            )['_id']

        self.headers = {
            'Authorization': 'Key %s' % self.api_key,
            'Content-type': 'application/json'
        }

    def tearDown(self):

        with self.app.app_context():
            db.destroy()

    def test_401_error(self):

        response = self.client.get('/alerts')
        self.assertEqual(response.status_code, 401)

    def test_readwrite_key(self):

        payload = {
            'user': 'rw-demo-key',
            'type': 'read-write'
        }

        response = self.client.post('/key', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-write key')

        rw_api_key = data['key']

        response = self.client.post('/alert', data=json.dumps(self.alert), content_type='application/json', headers={'Authorization': 'Key ' + rw_api_key})
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/alerts', headers={'Authorization': 'Key ' + rw_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('total', data)

        response = self.client.delete('/key/' + rw_api_key, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_readonly_key(self):

        payload = {
            'user': 'ro-demo-key',
            'type': 'read-only'
        }

        response = self.client.post('/key', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-only key')

        ro_api_key = data['key']

        response = self.client.post('/alert', data=json.dumps(self.alert), content_type='application/json', headers={'Authorization': 'Key ' + ro_api_key})
        self.assertEqual(response.status_code, 403)

        response = self.client.get('/alerts', headers={'Authorization': 'Key ' + ro_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('total', data)

        response = self.client.delete('/key/' + ro_api_key, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_users(self):

        # add customer mapping
        payload = {
            'customer': 'Bonaparte Industries',
            'match': 'bonaparte.fr'
        }
        response = self.client.post('/customer', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        payload = {
            'name': 'Napoleon Bonaparte',
            'email': 'napoleon@bonaparte.fr',
            'password': 'blackforest',
            'text': 'added to circle of trust'
        }

        # create user
        response = self.client.post('/auth/signup', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data, 'Failed to create user')

        with self.app.test_request_context():
            jwt = Jwt.parse(data['token'])
        user_id = jwt.subject

        # get user
        response = self.client.get('/users', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(user_id, [u['id'] for u in data['users']])

        # create duplicate user
        response = self.client.post('/auth/signup', data=json.dumps(payload), content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 409)

        # delete user
        response = self.client.delete('/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_login(self):

        name = 'Josephine de Beauharnais'

        payload = {
            'name': name,
            'email': 'josephine@debeauharnais.fr',
            'password': 'jojo',
            'text': 'Test login'
        }

        # sign-up user with no customer mapping
        response = self.client.post('/auth/signup', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 403)

        # add customer mapping
        payload = {
            'customer': 'Bonaparte Industries',
            'match': 'debeauharnais.fr'
        }
        response = self.client.post('/customer', data=json.dumps(payload), content_type='application/json', headers=self.headers)
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
            'user': 'customer-demo-key',
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
