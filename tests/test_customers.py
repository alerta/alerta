import json
import unittest

from flask import g

from alerta.app import create_app, db
from alerta.exceptions import ApiError
from alerta.models.enums import Scope
from alerta.models.key import ApiKey
from alerta.utils.api import assign_customer


class CustomersTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'ADMIN_USERS': ['admin@alerta.io'],
            'ALLOWED_EMAIL_DOMAINS': ['alerta.io', 'foo.com', 'bar.com']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.foo_alert = {
            'event': 'foo1',
            'resource': 'foo1',
            'environment': 'Production',
            'service': ['Web']
        }

        self.bar_alert = {
            'event': 'bar1',
            'resource': 'bar1',
            'environment': 'Production',
            'service': ['Web']
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.api_key = ApiKey(
                user='admin@alerta.io',
                scopes=[Scope.admin, Scope.read, Scope.write],
                text='admin-key'
            )
            self.api_key.create()

        self.admin_headers = {
            'Authorization': 'Key %s' % self.api_key.key,
            'Content-type': 'application/json'
        }

    def tearDown(self):
        db.destroy()

    def test_customers(self):

        # add customer mappings
        payload = {
            'customer': 'Bar Corp',
            'match': 'bar.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.admin_headers)
        self.assertEqual(response.status_code, 201)

        payload = {
            'customer': 'Foo Bar Corp',
            'match': 'foo@bar.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.admin_headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/customers', headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)

        # create users
        payload = {
            'name': 'Bar User',
            'email': 'user@bar.com',
            'password': 'b8rb8r',
            'text': ''
        }

        response = self.client.post('/auth/signup', data=json.dumps(payload),
                                    content_type='application/json', headers=self.admin_headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data, 'Failed to create user')

        self.bar_bearer_headers = {
            'Authorization': 'Bearer %s' % data['token'],
            'Content-type': 'application/json'
        }

        payload = {
            'name': 'Foo Bar User',
            'email': 'foo@bar.com',
            'password': 'f00b8r',
            'text': ''
        }

        response = self.client.post('/auth/signup', data=json.dumps(payload),
                                    content_type='application/json', headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data, 'Failed to create user')

        self.foobar_bearer_headers = {
            'Authorization': 'Bearer %s' % data['token'],
            'Content-type': 'application/json'
        }

        # create API key for user@bar.com
        payload = {
            'user': 'user@bar.com',
            'scopes': ['read', 'write'],
            'text': ''
        }

        response = self.client.post('/key', data=json.dumps(payload),
                                    content_type='application/json', headers=self.bar_bearer_headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-write key')

        self.bar_api_key_headers = {
            'Authorization': 'Key %s' % data['key'],
            'Content-type': 'application/json'
        }

        # create API keys for foo@bar.com
        payload = {
            'user': 'foo@bar.com',
            'scopes': ['read', 'write'],
            'text': '',
            'customer': 'Foo Bar Corp'
        }

        response = self.client.post('/key', data=json.dumps(payload),
                                    content_type='application/json', headers=self.foobar_bearer_headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-write key')

        self.foobar_api_key_headers = {
            'Authorization': 'Key %s' % data['key'],
            'Content-type': 'application/json'
        }

        payload = {
            'user': 'foo@bar.com',
            'scopes': ['read', 'write'],
            'text': '',
            'customer': 'Bar Corp'
        }

        response = self.client.post('/key', data=json.dumps(payload),
                                    content_type='application/json', headers=self.foobar_bearer_headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data['key'], 'Failed to create read-write key')

        self.foobar_bar_only_api_key_headers = {
            'Authorization': 'Key %s' % data['key'],
            'Content-type': 'application/json'
        }

        # get list of customers for users
        response = self.client.get('/customers', headers=self.bar_api_key_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual([c['customer'] for c in data['customers']], ['Bar Corp'])

        response = self.client.get('/customers', headers=self.foobar_api_key_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual([c['customer'] for c in data['customers']], ['Foo Bar Corp'])

        # create alerts using API keys
        response = self.client.post('/alert', data=json.dumps(self.foo_alert), headers=self.bar_api_key_headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['customer'], 'Bar Corp')

        response = self.client.post('/alert', data=json.dumps(self.foo_alert), headers=self.foobar_api_key_headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['customer'], 'Foo Bar Corp')

        response = self.client.post('/alert', data=json.dumps(self.foo_alert),
                                    headers=self.foobar_bar_only_api_key_headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['customer'], 'Bar Corp')

        response = self.client.post('/alert', data=json.dumps(self.foo_alert),
                                    headers=self.foobar_bar_only_api_key_headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['customer'], 'Bar Corp')

        # create alerts using Bearer tokens
        response = self.client.post('/alert', data=json.dumps(self.foo_alert), headers=self.bar_bearer_headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['customer'], 'Bar Corp')

        self.foo_alert['customer'] = 'Foo Bar Corp'
        response = self.client.post('/alert', data=json.dumps(self.foo_alert), headers=self.foobar_bearer_headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['customer'], 'Foo Bar Corp')

    def test_blackouts(self):

        # add customer mappings
        payload = {
            'customer': 'Foo Corp',
            'match': 'foo.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.admin_headers)
        self.assertEqual(response.status_code, 201)

        payload = {
            'customer': 'Bar Corp',
            'match': 'bar.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.admin_headers)
        self.assertEqual(response.status_code, 201)

        # create users
        payload = {
            'name': 'Foo User',
            'email': 'user@foo.com',
            'password': 'f00f00',
            'text': ''
        }

        response = self.client.post('/auth/signup', data=json.dumps(payload),
                                    content_type='application/json', headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data, 'Failed to create user')

        foo_user_headers = {
            'Authorization': 'Bearer %s' % data['token'],
            'Content-type': 'application/json'
        }

        payload = {
            'name': 'Bar User',
            'email': 'user@bar.com',
            'password': 'b8rb8r',
            'text': ''
        }

        response = self.client.post('/auth/signup', data=json.dumps(payload),
                                    content_type='application/json', headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIsNotNone(data, 'Failed to create user')

        bar_user_headers = {
            'Authorization': 'Bearer %s' % data['token'],
            'Content-type': 'application/json'
        }

        # create customer blackout by foo user
        response = self.client.post(
            '/blackout', data=json.dumps({'environment': 'Production'}), headers=foo_user_headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # new alert by foo user should be suppressed
        response = self.client.post('/alert', data=json.dumps(self.foo_alert), headers=foo_user_headers)
        self.assertEqual(response.status_code, 202)

        # new alert by bar user should not be suppressed
        response = self.client.post('/alert', data=json.dumps(self.bar_alert), headers=bar_user_headers)
        self.assertEqual(response.status_code, 201)

        # delete blackout by id
        response = self.client.delete('/blackout/' + blackout_id, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)

        # create global blackout by admin user
        response = self.client.post(
            '/blackout', data=json.dumps({'environment': 'Production'}), headers=self.admin_headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        blackout_id = data['id']

        # new alert by foo user should be suppressed
        response = self.client.post('/alert', data=json.dumps(self.foo_alert), headers=foo_user_headers)
        self.assertEqual(response.status_code, 202)

        # new alert by bar user should be suppressed
        response = self.client.post('/alert', data=json.dumps(self.bar_alert), headers=bar_user_headers)
        self.assertEqual(response.status_code, 202)

        # delete blackout by id
        response = self.client.delete('/blackout/' + blackout_id, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)

    def test_assign_customer(self):

        with self.app.test_request_context('/'):
            self.app.preprocess_request()

            # nothing wanted, assign one
            g.customers = ['Customer1']
            g.scopes = []
            self.assertEqual(assign_customer(wanted=None), 'Customer1')

            # nothing wanted, but too many, throw error
            g.customers = ['Customer1', 'Customer2']
            g.scopes = []
            with self.assertRaises(ApiError) as e:
                assign_customer(wanted=None)
            exc = e.exception
            self.assertEqual(str(exc), 'must define customer as more than one possibility')

            # customer wanted, matches so allow
            g.customers = ['Customer1']
            g.scopes = []
            self.assertEqual(assign_customer(wanted='Customer1'), 'Customer1')

            # customer wanted, in list so allow
            g.customers = ['Customer1', 'Customer2']
            g.scopes = []
            self.assertEqual(assign_customer(wanted='Customer2'), 'Customer2')

            # customer wanted not in list, throw exception
            g.customers = ['Customer1', 'Customer2']
            g.scopes = []
            with self.assertRaises(ApiError) as e:
                assign_customer(wanted='Customer3')
            exc = e.exception
            self.assertEqual(str(exc), "not allowed to set customer to 'Customer3'")

            # no customers, admin scope so allow
            g.customers = []
            g.scopes = ['admin']
            self.assertEqual(assign_customer(wanted=None), None)
            self.assertEqual(assign_customer(wanted='Customer1'), 'Customer1')

            g.customers = ['Customer1', 'Customer2']
            g.scopes = ['admin']
            with self.assertRaises(ApiError) as e:
                assign_customer(wanted=None)
            exc = e.exception
            self.assertEqual(str(exc), 'must define customer as more than one possibility')
            self.assertEqual(assign_customer(wanted='Customer3'), 'Customer3')

            # wrong scope
            g.customers = ['Customer1']
            g.scopes = ['read:keys', 'write:keys']
            with self.assertRaises(ApiError) as e:
                assign_customer(wanted='Customer2', permission=Scope.admin_keys)
            exc = e.exception
            self.assertEqual(str(exc), "not allowed to set customer to 'Customer2'")

            # right scope
            g.customers = ['Customer1']
            g.scopes = ['admin:keys', 'read:keys', 'write:keys']
            self.assertEqual(assign_customer(wanted='Customer2', permission=Scope.admin_keys), 'Customer2')

    def test_invalid_customer(self):

        self.foo_alert['customer'] = ''

        response = self.client.post('/alert', data=json.dumps(self.foo_alert), headers=self.admin_headers)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['message'], 'customer must not be an empty string')

    def test_edit_customer(self):

        # add customer mappings
        payload = {
            'customer': 'Foo Corp',
            'match': 'foo.com'
        }
        response = self.client.post('/customer', data=json.dumps(payload),
                                    content_type='application/json', headers=self.admin_headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        customer_id = data['id']

        # change customer name
        update = {
            'customer': 'Bar Corp'
        }
        response = self.client.put('/customer/' + customer_id, data=json.dumps(update), headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        # check updates worked and didn't change anything else
        response = self.client.get('/customer/' + customer_id, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['customer']['customer'], 'Bar Corp')
        self.assertEqual(data['customer']['match'], 'foo.com')

        # change customer lookup
        update = {
            'match': 'bar.com'
        }
        response = self.client.put('/customer/' + customer_id, data=json.dumps(update), headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['status'], 'ok')

        # check updates worked and didn't change anything else
        response = self.client.get('/customer/' + customer_id, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['customer']['customer'], 'Bar Corp')
        self.assertEqual(data['customer']['match'], 'bar.com')
