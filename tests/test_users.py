import json
import unittest

from alerta.app import create_app, db
from alerta.models.enums import Scope
from alerta.models.key import ApiKey


class UsersTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'ADMIN_USERS': ['admin@alerta.io'],
            'ALLOWED_EMAIL_DOMAINS': ['alerta.io', 'doe.com']
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

    def test_user(self):

        payload = {
            'name': 'John Doe',
            'email': 'john@doe.com',
            'password': 'p8ssw0rd',
            'roles': ['operator'],
            'text': 'devops user'
        }

        # create user
        response = self.client.post('/user', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['user']['name'], 'John Doe')
        self.assertEqual(data['user']['email'], 'john@doe.com')
        self.assertEqual(data['user']['roles'], ['operator'])
        self.assertEqual(data['user']['email_verified'], False)

        user_id = data['id']

        payload = {
            'role': 'devops'
        }

        # modify user (assign different role)
        response = self.client.put('/user/' + user_id, data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        # get user
        response = self.client.get('/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['user']['name'], 'John Doe')
        self.assertEqual(data['user']['email'], 'john@doe.com')
        self.assertEqual(data['user']['roles'], ['devops'])
        self.assertEqual(data['user']['email_verified'], False)

        payload = {
            'roles': ['devops', 'operator', 'user']
        }

        # modify user (assign multiple roles)
        response = self.client.put('/user/' + user_id, data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        # get user
        response = self.client.get('/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['user']['name'], 'John Doe')
        self.assertEqual(data['user']['email'], 'john@doe.com')
        self.assertEqual(data['user']['roles'], ['devops', 'operator', 'user'])
        self.assertEqual(data['user']['email_verified'], False)

    def test_user_attributes(self):

        payload = {
            'name': 'John Doe',
            'email': 'john@doe.com',
            'password': 'p8ssw0rd',
            'roles': ['operator'],
            'text': 'devops user'
        }

        # create user
        response = self.client.post('/user', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['user']['name'], 'John Doe')
        self.assertEqual(data['user']['login'], 'john@doe.com')
        self.assertEqual(data['user']['roles'], ['operator'])
        self.assertEqual(data['user']['email'], 'john@doe.com')
        self.assertEqual(data['user']['email_verified'], False)

        payload = {
            'email': 'john@doe.com',
            'password': 'p8ssw0rd'
        }

        # login using new user
        response = self.client.post('/auth/login', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('token', data)

        token = data['token']

        headers = {
            'Authorization': 'Bearer ' + token,
            'Content-type': 'application/json'
        }

        payload = {
            'attributes': {
                'prefs': {
                    'isDark': True
                }
            }
        }
        # set user attribute
        response = self.client.put('/user/me/attributes', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        # get user attribute
        response = self.client.get('/user/me/attributes', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['attributes']['prefs'], {'isDark': True})

        payload = {
            'attributes': {
                'prefs': {
                    'isMute': False,
                    'refreshInterval': 5000
                }
            }
        }
        # set user attribute
        response = self.client.put('/user/me/attributes', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        # get user attribute
        response = self.client.get('/user/me/attributes', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['attributes']['prefs'], {'isDark': True, 'isMute': False, 'refreshInterval': 5000})

        payload = {
            'attributes': {
                'prefs': {
                    'isMute': None
                }
            }
        }
        # unset user attribute
        response = self.client.put('/user/me/attributes', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        # get user attribute
        response = self.client.get('/user/me/attributes', data=json.dumps(payload), headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['attributes']['prefs'], {'isDark': True, 'isMute': None, 'refreshInterval': 5000})
