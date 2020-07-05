import json
import unittest

from alerta.app import create_app, db
from alerta.models.enums import ADMIN_SCOPES
from alerta.models.key import ApiKey


class AlertNotesTestCase(unittest.TestCase):

    def setUp(self):
        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'PLUGINS': ['reject']
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.prod_alert = {
            'resource': 'node404',
            'event': 'node_down',
            'environment': 'Production',
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'service': ['Core', 'Web', 'Network'],
            'group': 'Network',
            'tags': ['level=20', 'switch:off']
        }

        self.dev_alert = {
            'resource': 'node404',
            'event': 'node_marginal',
            'environment': 'Development',
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'service': ['Core', 'Web', 'Network'],
            'group': 'Network',
            'tags': ['level=20', 'switch:off']
        }

        self.fatal_alert = {
            'event': 'node_down',
            'resource': 'net01',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'foo': 'abc def', 'bar': 1234, 'baz': False},
        }
        self.critical_alert = {
            'event': 'node_marginal',
            'resource': 'net02',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 30
        }
        self.major_alert = {
            'event': 'node_marginal',
            'resource': 'net03',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 40
        }
        self.normal_alert = {
            'event': 'node_up',
            'resource': 'net03',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'normal',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 100
        }

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            self.admin_api_key = ApiKey(
                user='admin@alerta.io',
                scopes=ADMIN_SCOPES,
                text='demo-key'
            )
            self.customer_api_key = ApiKey(
                user='admin@alerta.io',
                scopes=ADMIN_SCOPES,
                text='demo-key',
                customer='Foo'
            )
            self.admin_api_key.create()
            self.customer_api_key.create()

    def tearDown(self):
        db.destroy()

    def test_alert_notes(self):

        self.headers = {
            'Authorization': 'Key %s' % self.admin_api_key.key,
            'Content-type': 'application/json'
        }

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.prod_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        alert_id = data['id']

        # get alert
        response = self.client.get('/alert/{}'.format(alert_id), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        # add note to alert
        note = {
            'text': 'this is a note'
        }
        response = self.client.put('/alert/{}/note'.format(alert_id), data=json.dumps(note), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        note_id = data['id']

        self.assertEqual(data['note']['text'], 'this is a note')
        self.assertEqual(data['note']['user'], 'admin@alerta.io')
        self.assertEqual(
            sorted(data['note']['attributes']),
            sorted({'resource': 'node404', 'event': 'node_down', 'environment': 'Production', 'severity': 'major', 'status': 'open'})
        )
        self.assertEqual(data['note']['type'], 'alert')
        self.assertIsNotNone(data['note']['createTime'])
        self.assertIsNone(data['note']['updateTime'])
        self.assertIn(alert_id, data['note']['_links']['alert'])
        self.assertEqual(data['note']['customer'], None)

        # list notes for alert
        response = self.client.get('/alert/{}/notes'.format(alert_id), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['notes'][0]['id'], note_id)
        self.assertEqual(data['notes'][0]['text'], 'this is a note')

        # update note text
        note = {
            'text': 'this note has changed'
        }
        response = self.client.put('/alert/{}/note/{}'.format(alert_id, note_id), data=json.dumps(note), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(data['status'], 'ok')

        self.assertEqual(data['note']['text'], 'this note has changed')
        self.assertEqual(data['note']['user'], 'admin@alerta.io')
        self.assertEqual(
            sorted(data['note']['attributes']),
            sorted({'resource': 'node404', 'event': 'node_down', 'environment': 'Production', 'severity': 'major', 'status': 'open'})
        )
        self.assertEqual(data['note']['type'], 'alert')
        self.assertIsNotNone(data['note']['createTime'])
        self.assertIsNotNone(data['note']['updateTime'])
        self.assertIn(alert_id, data['note']['_links']['alert'])
        self.assertEqual(data['note']['customer'], None)

        # list notes for alert (again)
        response = self.client.get('/alert/{}/notes'.format(alert_id), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['notes'][0]['id'], note_id)
        self.assertEqual(data['notes'][0]['text'], 'this note has changed')

        # delete note
        response = self.client.delete('/alert/{}/note/{}'.format(alert_id, note_id), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))

        self.assertEqual(data['status'], 'ok')
