import base64
import json
import unittest

from mohawk import Sender

from alerta.app import create_app, db, plugins
from alerta.models.enums import Scope
from alerta.models.key import ApiKey
from alerta.models.token import Jwt


class AuthTestCase(unittest.TestCase):

    def setUp(self):

        self.access_key = 'cc3b7f30-360e-47bc-8abb-c0a27625e134'
        self.secret_key = 'MjM0ODU4NGI1YWQxZWMyYzcxNjAxZDA4MzczNGQ1M2IK'

        test_config = {
            'DEBUG': True,
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'ADMIN_USERS': ['admin@alerta.io'],
            'DELETE_SCOPES': ['delete:alerts'],
            'ALLOWED_EMAIL_DOMAINS': ['bonaparte.fr', 'debeauharnais.fr', 'manorfarm.ru'],
            'HMAC_AUTH_CREDENTIALS': [
                {
                    'key': self.access_key,
                    'secret': self.secret_key,
                    'algorithm': 'sha256'
                }
            ]
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
                text='Demo API key - not for production use',
                key='demo-key'
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

    def test_user_defined_key(self):

        self.assertEqual(self.api_key.key, 'demo-key')

    def test_admin_key(self):

        payload = {
            'user': 'rw-demo-key-user',
            'scopes': ['admin']
        }

        response = self.client.post('/key', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-write key')

        admin_api_key = data['key']

        response = self.client.post('/alert', data=json.dumps(self.alert),
                                    content_type='application/json', headers={'Authorization': 'Key ' + admin_api_key})
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['history'][0]['user'], 'rw-demo-key-user')

        alert_id = data['id']

        response = self.client.get('/alerts', headers={'Authorization': 'Key ' + admin_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('total', data)

        response = self.client.get('/key/' + admin_api_key, headers={'Authorization': 'Key ' + admin_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['key']['scopes'], ['admin'])

        # delete alert
        response = self.client.delete('/alert/' + alert_id, headers={'Authorization': 'Key ' + admin_api_key})
        self.assertEqual(response.status_code, 200)

        response = self.client.delete('/key/' + admin_api_key, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_readwrite_key(self):

        payload = {
            'user': 'rw-demo-key-user',
            'type': 'read-write'
        }

        response = self.client.post('/key', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-write key')

        rw_api_key = data['key']

        response = self.client.post('/alert', data=json.dumps(self.alert),
                                    content_type='application/json', headers={'Authorization': 'Key ' + rw_api_key})
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['history'][0]['user'], 'rw-demo-key-user')

        alert_id = data['id']

        response = self.client.get('/alerts', headers={'Authorization': 'Key ' + rw_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('total', data)

        response = self.client.get('/key/' + rw_api_key, headers={'Authorization': 'Key ' + rw_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['key']['scopes'], ['read', 'write'])

        # delete alert
        response = self.client.delete('/alert/' + alert_id, headers={'Authorization': 'Key ' + rw_api_key})
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['message'], 'Missing required scope: delete:alerts')

        response = self.client.delete('/key/' + rw_api_key, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_rw_delete_key(self):

        payload = {
            'user': 'rw-delete-demo-key-user',
            'scopes': ['read', 'write', 'delete:alerts']
        }

        response = self.client.post('/key', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-write-delete key')
        self.assertEqual(data['data']['scopes'], ['read', 'write', 'delete:alerts'])

        rwd_api_key = data['key']

        response = self.client.post('/alert', data=json.dumps(self.alert),
                                    content_type='application/json', headers={'Authorization': 'Key ' + rwd_api_key})
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['history'][0]['user'], 'rw-delete-demo-key-user')

        alert_id = data['id']

        response = self.client.get('/alerts', headers={'Authorization': 'Key ' + rwd_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('total', data)

        response = self.client.get('/key/' + rwd_api_key, headers={'Authorization': 'Key ' + rwd_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['key']['scopes'], ['read', 'write', 'delete:alerts'])

        # delete alert
        response = self.client.delete('/alert/' + alert_id, headers={'Authorization': 'Key ' + rwd_api_key})
        self.assertEqual(response.status_code, 200)

        response = self.client.delete('/key/' + rwd_api_key, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_readonly_key(self):

        payload = {
            'user': 'ro-demo-key-user',
            'type': 'read-only'
        }

        response = self.client.post('/key', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-only key')

        ro_api_key = data['key']

        response = self.client.post('/alert', data=json.dumps(self.alert),
                                    content_type='application/json', headers={'Authorization': 'Key ' + ro_api_key})
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
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        payload = {
            'name': 'Napoleon Bonaparte',
            'email': 'napoleon@bonaparte.fr',
            'password': 'blackforest',
            'text': 'added to circle of trust'
        }

        # create user
        response = self.client.post('/auth/signup', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
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
        response = self.client.post('/auth/signup', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
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

    def test_x_api_key(self):

        self.headers = {
            'X-API-Key': self.api_key.key,
            'Content-type': 'application/json'
        }

        payload = {
            'user': 'rw-demo-key-user',
            'type': 'read-write'
        }

        response = self.client.post('/key', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-write key')

        rw_api_key = data['key']

        response = self.client.post('/alert', data=json.dumps(self.alert),
                                    content_type='application/json', headers={'X-API-Key': rw_api_key})
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/alerts', headers={'X-API-Key': rw_api_key})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('total', data)

        response = self.client.delete('/key/' + rw_api_key, headers=self.headers)
        self.assertEqual(response.status_code, 200)

    def test_edit_api_keys(self):

        self.headers = {
            'Authorization': f'Key {self.api_key.key}',
            'Content-type': 'application/json'
        }

        # create api key
        payload = {
            'scopes': [Scope.read, Scope.write_alerts, Scope.write_blackouts],
            'text': 'devops automation key',
            'expireTime': '2099-12-31T23:59:59.999Z'
        }
        response = self.client.post('/key', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        api_key_id = data['key']

        # extend blackout period & change environment
        update = {
            'scopes': [Scope.read, Scope.write_blackouts, Scope.write_webhooks],
            'expireTime': '2022-12-31T23:59:59.999Z'
        }
        response = self.client.put('/key/' + api_key_id, data=json.dumps(update), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        # check updates worked and didn't change anything else
        response = self.client.get('/key/' + api_key_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['key']['scopes'], [Scope.read, Scope.write_blackouts, Scope.write_webhooks])
        self.assertEqual(data['key']['user'], 'admin@alerta.io')
        self.assertEqual(data['key']['text'], 'devops automation key')
        self.assertEqual(data['key']['expireTime'], '2022-12-31T23:59:59.999Z')

    def test_basic_auth(self):

        # add customer mapping
        payload = {
            'customer': 'Bonaparte Industries',
            'match': 'bonaparte.fr'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        payload = {
            'name': 'Napoleon Bonaparte',
            'email': 'napoleon@bonaparte.fr',
            'password': 'blackforest',
            'text': 'added to circle of trust'
        }

        # create user
        response = self.client.post('/auth/signup', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # authenticate using basic auth
        headers = {
            'Authorization': 'Basic ' + base64.b64encode(b'napoleon@bonaparte.fr:blackforest').decode(),
            'Content-type': 'application/json'
        }

        response = self.client.get('/users', headers=headers)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['message'], 'Missing required scope: admin:users')

        response = self.client.get('/alerts', headers=headers)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok', response.data)

    def test_edit_user(self):

        # add customer mapping
        payload = {
            'customer': 'Manor Farm',
            'match': 'manorfarm.ru'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.headers)
        self.assertEqual(response.status_code, 201)

        payload = {
            'name': 'Snowball',
            'email': 'snowball@manorfarm.ru',
            'password': 'Postoronii',
            'text': 'Can you not understand that liberty is worth more than ribbons?',
            'attributes': {'two-legs': 'bad', 'hasFourLegs': True, 'isEvil': False}
        }

        # create user
        response = self.client.post('/auth/signup', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        with self.app.test_request_context():
            jwt = Jwt.parse(data['token'])
        user_id = jwt.subject

        # get user
        response = self.client.get('/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['user']['name'], 'Snowball')
        self.assertEqual(data['user']['email'], 'snowball@manorfarm.ru')
        self.assertEqual(data['user']['text'], 'Can you not understand that liberty is worth more than ribbons?')

        # FIXME: attribute keys with None (null) values aren't deleted in postgres

        # change user details
        update = {
            'name': 'Squealer',
            'text': 'Four legs good, two legs bad.',
            'attributes': {'four-legs': 'good', 'isEvil': True}
        }
        response = self.client.put('/user/' + user_id, data=json.dumps(update), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        # check updates worked and didn't change anything else
        response = self.client.get('/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['user']['name'], 'Squealer')
        self.assertEqual(data['user']['email'], 'snowball@manorfarm.ru')
        self.assertEqual(data['user']['text'], 'Four legs good, two legs bad.')
        self.assertEqual(data['user']['attributes'], {
            'four-legs': 'good',
            'two-legs': 'bad',
            'hasFourLegs': True,
            'isEvil': True
        })

        # just update attributes
        update = {
            'attributes': {'four-legs': 'double good', 'isEvil': False, 'hasFourLegs': None}
        }
        response = self.client.put('/user/' + user_id + '/attributes', data=json.dumps(update), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        # check updates worked and didn't change anything else
        response = self.client.get('/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['user']['name'], 'Squealer')
        self.assertEqual(data['user']['email'], 'snowball@manorfarm.ru')
        self.assertEqual(data['user']['text'], 'Four legs good, two legs bad.')
        self.assertEqual(data['user']['attributes'], {
            'four-legs': 'double good',
            'two-legs': 'bad',
            'isEvil': False
        })

    def test_hmac_auth(self):

        credentials = {
            'id': self.access_key,
            'key': self.secret_key,
            'algorithm': 'sha256'
        }

        sender = Sender(
            url='http://localhost/alerts',
            method='GET',
            content='',
            content_type='application/json',
            credentials=credentials
        )
        headers = {
            'Authorization': sender.request_header,
            'Content-Type': 'application/json'
        }
        response = self.client.get('/alerts', headers=headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        sender = Sender(
            url='http://localhost/alert',
            method='POST',
            content=json.dumps(self.alert),
            content_type='application/json',
            credentials=credentials
        )
        headers = {
            'Authorization': sender.request_header,
            'Content-Type': 'application/json'
        }
        response = self.client.post('/alert', data=json.dumps(self.alert),
                                    content_type='application/json', headers=headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['event'], 'Foo')
