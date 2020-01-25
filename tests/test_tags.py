import json
import unittest
from uuid import uuid4

from alerta.app import create_app, db


class TagsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.resource = str(uuid4()).upper()[:8]

        self.node_down_alert = {
            'event': 'node_down',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'ip': '10.0.3.4'}
        }

        self.node_up_alert = {
            'event': 'node_up',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'normal',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'ip': '10.0.3.4'}
        }

        self.headers = {
            'Content-type': 'application/json'
        }

    def tearDown(self):
        db.destroy()

    def test_tag_alert(self):

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.node_down_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['tags'], ['foo'])

        alert_id = data['id']

        # tag alert
        response = self.client.put('/alert/%s/tag' %
                                   alert_id, data=json.dumps({'tags': ['bar', 'baz']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # duplicate alert
        response = self.client.post('/alert', data=json.dumps(self.node_down_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(sorted(data['alert']['tags']), sorted(['foo', 'bar', 'baz']))
        self.assertEqual(data['alert']['duplicateCount'], 1)

        # tag alert
        response = self.client.put('/alert/%s/tag' %
                                   alert_id, data=json.dumps({'tags': ['quux']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # correlate alert
        response = self.client.post('/alert', data=json.dumps(self.node_up_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(sorted(data['alert']['tags']), sorted(['foo', 'bar', 'baz', 'quux']))

        # untag alert
        response = self.client.put('/alert/%s/untag' %
                                   alert_id, data=json.dumps({'tags': ['quux']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # duplicate alert (again)
        response = self.client.post('/alert', data=json.dumps(self.node_up_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(sorted(data['alert']['tags']), sorted(['foo', 'bar', 'baz']))
