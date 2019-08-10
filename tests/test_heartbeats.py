
import json
import unittest
from uuid import uuid4

from alerta.app import create_app, db


class HeartbeatsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'HEARTBEAT_TIMEOUT': 240
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.origin = str(uuid4()).upper()[:8]

        self.heartbeat = {
            'origin': self.origin,
            'tags': ['foo', 'bar', 'baz']
        }

        self.headers = {
            'Content-type': 'application/json'
        }

    def tearDown(self):
        db.destroy()

    def test_heartbeat(self):

        # create heartbeat
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['heartbeat']['origin'], self.origin)
        self.assertListEqual(data['heartbeat']['tags'], self.heartbeat['tags'])

        heartbeat_id = data['id']

        # create duplicate heartbeat
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(heartbeat_id, data['heartbeat']['id'])

        # get heartbeat
        response = self.client.get('/heartbeat/' + heartbeat_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(heartbeat_id, data['heartbeat']['id'])

        # delete heartbeat
        response = self.client.delete('/heartbeat/' + heartbeat_id)
        self.assertEqual(response.status_code, 200)

    def test_heartbeat_not_found(self):

        response = self.client.get('/heartbeat/doesnotexist')
        self.assertEqual(response.status_code, 404)

    def test_get_heartbeats(self):

        # create heartbeat
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.get('/heartbeats')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertGreater(data['total'], 0, 'total heartbeats > 0')

    def test_timeout(self):

        # create heartbeat with default timeout
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['heartbeat']['timeout'], 240)

        # resend alert with different timeout
        self.heartbeat['timeout'] = 20
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['heartbeat']['timeout'], 20)

        # resend alert with timeout disabled (ie. 0)
        self.heartbeat['timeout'] = 0
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['heartbeat']['timeout'], 0)

        # send heartbeat with different timeout
        self.heartbeat['timeout'] = 10
        response = self.client.post('/heartbeat', data=json.dumps(self.heartbeat), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['heartbeat']['timeout'], 10)

    def test_heartbeat_from_alert(self):

        heartbeat_alert = {
            'event': 'Heartbeat',
            'resource': 'net01',
            'environment': 'Production',
            'service': ['Svc1'],
            'origin': 'test/hb',
            'timeout': 500
        }

        response = self.client.post('/alert', data=json.dumps(heartbeat_alert), headers=self.headers)
        self.assertEqual(response.status_code, 202, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['message'], 'Alert converted to heartbeat')

        response = self.client.get('/heartbeats?origin=test/hb')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['heartbeats'][0]['origin'], 'test/hb')
        self.assertEqual(data['heartbeats'][0]['timeout'], 500)

        prometheus_alert = r"""
        {
          "receiver": "alerta",
          "status": "firing",
          "alerts": [
            {
              "status": "firing",
              "labels": {
                "alertname": "Heartbeat",
                "dc": "eu-west-1",
                "environment": "Production",
                "monitor": "codelab",
                "region": "EU",
                "service": "Prometheus",
                "severity": "informational"
              },
              "annotations": {},
              "startsAt": "2019-04-15T14:14:22.012771244Z",
              "endsAt": "0001-01-01T00:00:00Z",
              "generatorURL": "http://96b678727a4b:9090/graph?g0.expr=vector%281%29\u0026g0.tab=1"
            }
          ],
          "groupLabels": {
            "alertname": "Heartbeat"
          },
          "commonLabels": {
            "alertname": "Heartbeat",
            "dc": "eu-west-1",
            "environment": "Production",
            "monitor": "codelab",
            "region": "EU",
            "service": "Prometheus",
            "severity": "informational"
          },
          "commonAnnotations": {},
          "externalURL": "http://316cdde530cd:9093",
          "version": "4",
          "groupKey": "{}:{alertname=\"Heartbeat\"}"
        }
        """

        response = self.client.post('/webhooks/prometheus', data=prometheus_alert, headers=self.headers)
        self.assertEqual(response.status_code, 202)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['message'], 'Alert converted to heartbeat')

        response = self.client.get('/heartbeats?origin=prometheus/codelab')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(sorted(data['heartbeats'][0]['tags']), sorted(['dc=eu-west-1', 'region=EU']))
