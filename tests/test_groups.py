import json
import unittest

from alerta.app import create_app, db
from alerta.models.enums import Scope
from alerta.models.key import ApiKey


class GroupsTestCase(unittest.TestCase):

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

    def test_groups(self):

        # create a group
        payload = {
            'name': 'Group 1',
            'text': 'Test group #1'
        }
        response = self.client.post('/group', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['group']['name'], 'Group 1')
        self.assertEqual(data['group']['text'], 'Test group #1')

        group_id = data['group']['id']

        # get group
        response = self.client.get('/group/' + group_id, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['group']['name'], 'Group 1')
        self.assertEqual(data['group']['text'], 'Test group #1')

        # create a duplicate group name
        # payload = {
        #     'name': 'Group 1',
        #     'text': 'Test group #1 duplicate'
        # }
        # response = self.client.post('/group', data=json.dumps(payload), headers=self.headers)
        # self.assertEqual(response.status_code, 500, response.data)

        # update a group name, text
        payload = {
            'name': 'Group 1 changed',
            'text': 'Test group #1 changed too'
        }
        response = self.client.put('/group/' + group_id, data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)

        response = self.client.get('/group/' + group_id, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['group']['name'], 'Group 1 changed')
        self.assertEqual(data['group']['text'], 'Test group #1 changed too')

        # create a different group
        payload = {
            'name': 'Group 2',
            'text': 'Test group #2'
        }
        response = self.client.post('/group', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['group']['name'], 'Group 2')
        self.assertEqual(data['group']['text'], 'Test group #2')

        group2_id = data['group']['id']

        # list groups
        response = self.client.get('/groups', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertListEqual([g['name'] for g in data['groups']], ['Group 1 changed', 'Group 2'])

        # create a user
        payload = {
            'name': 'John Doe',
            'email': 'john@doe.com',
            'password': 'p8ssw0rd',
            'roles': ['operator'],
            'text': 'devops user'
        }

        response = self.client.post('/user', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['user']['name'], 'John Doe')

        user_id = data['user']['id']

        # add a user to first group
        response = self.client.put('/group/' + group_id + '/user/' + user_id, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))

        # get users for first group
        response = self.client.get('/group/' + group_id + '/users', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertListEqual([u['name'] for u in data['users']], ['John Doe'])

        # create another user
        payload = {
            'name': 'Jane Doe',
            'email': 'jane@doe.com',
            'password': 'p8ssw0rd',
            'roles': ['manager'],
            'text': 'manager'
        }

        response = self.client.post('/user', data=json.dumps(payload), headers=self.headers)
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['user']['name'], 'Jane Doe')

        user2_id = data['user']['id']

        # add another user to first group
        response = self.client.put('/group/' + group_id + '/user/' + user2_id, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))

        # get users for first group again
        response = self.client.get('/group/' + group_id + '/users', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertListEqual([u['name'] for u in data['users']], ['John Doe', 'Jane Doe'])

        # add second user to second group
        response = self.client.put('/group/' + group2_id + '/user/' + user2_id, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))

        # get users for second group
        response = self.client.get('/group/' + group2_id + '/users', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertListEqual([u['name'] for u in data['users']], ['Jane Doe'])

        # get groups for first user
        response = self.client.get('/user/' + user_id + '/groups', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertListEqual([g['name'] for g in data['groups']], ['Group 1 changed'])

        # get groups for second user
        response = self.client.get('/user/' + user2_id + '/groups', headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertListEqual([g['name'] for g in data['groups']], ['Group 1 changed', 'Group 2'])

        # delete groups
        response = self.client.delete('/group/' + group_id, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)

        response = self.client.delete('/group/' + group2_id, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
