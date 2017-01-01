
import unittest

try:
    import simplejson as json
except ImportError:
    import json

from uuid import uuid4
from alerta.app import app, db


class TagTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        self.app = app.test_client()

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

        db.destroy_db()

    def test_tag_alert(self):

        # create alert
        response = self.app.post('/alert', data=json.dumps(self.node_down_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['tags'], ['foo'])

        alert_id = data['id']

        # tag alert
        response = self.app.put('/alert/%s/tag' % alert_id, data=json.dumps({'tags': ['bar', 'baz']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # duplicate alert
        response = self.app.post('/alert', data=json.dumps(self.node_down_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['tags'], ['foo', 'bar', 'baz'])
        self.assertEqual(data['alert']['duplicateCount'], 1)

        # tag alert
        response = self.app.put('/alert/%s/tag' % alert_id, data=json.dumps({'tags': ['quux']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # correlate alert
        response = self.app.post('/alert', data=json.dumps(self.node_up_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['tags'], ['foo', 'bar', 'baz', 'quux'])

        # untag alert
        response = self.app.put('/alert/%s/untag' % alert_id, data=json.dumps({'tags': ['quux']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # duplicate alert (again)
        response = self.app.post('/alert', data=json.dumps(self.node_up_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['tags'], ['foo', 'bar', 'baz'])
