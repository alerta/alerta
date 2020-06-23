import json
import unittest
from uuid import uuid4

from alerta.app import create_app, db


class AggregationsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'ALERT_TIMEOUT': 120,
            'HISTORY_LIMIT': 5
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        def random_resource():
            return str(uuid4()).upper()[:8]

        self.fatal_alert = {
            'event': 'node_down',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network', 'Shared'],
            'group': 'Network',
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'foo': 'abc def', 'bar': 1234, 'baz': False},
        }
        self.critical_alert = {
            'event': 'node_marginal',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'group': 'Nw',
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['bar'],
            'timeout': 30
        }
        self.major_alert = {
            'event': 'node_marginal',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network', 'Shared'],
            'group': 'Network',
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['baz'],
            'timeout': 40
        }
        self.warn_alert = {
            'event': 'node_marginal',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'group': 'net',
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['quux'],
            'timeout': 50
        }
        self.normal_alert = {
            'event': 'node_up',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'group': 'Network',
            'severity': 'normal',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['quux'],
            'timeout': 100
        }

        self.ok_alert = {
            'event': 'node_up',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'group': 'nw',
            'severity': 'ok',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['quux'],
        }

        self.cleared_alert = {
            'event': 'node_up',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'group': 'Network',
            'severity': 'cleared',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
        }

        self.ok2_alert = {
            'event': 'node_up',
            'resource': random_resource(),
            'environment': 'Production',
            'service': ['Network'],
            'group': 'Network',
            'severity': 'ok',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['bar'],
        }

        self.headers = {
            'Content-type': 'application/json',
            'X-Forwarded-For': '10.0.0.1'
        }

    def tearDown(self):
        db.destroy()

    def test_aggregations(self):

        # create alerts
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/alert', data=json.dumps(self.ok_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/alert', data=json.dumps(self.cleared_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        response = self.client.post('/alert', data=json.dumps(self.ok2_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # counts
        response = self.client.get('/alerts/count')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('statusCounts', data)
        self.assertIn('severityCounts', data)

        # top 10 count
        response = self.client.get('/alerts/top10/count')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('top10', data)

        # top 10 flapping
        response = self.client.get('/alerts/top10/flapping')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('top10', data)

        # top 10 standing
        response = self.client.get('/alerts/top10/standing')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('top10', data)

        # environments
        response = self.client.get('/environments')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('environments', data)
        self.assertCountEqual(data['environments'], [
            {
                'count': 8,
                'environment': 'Production',
                'severityCounts': {
                    'cleared': 1,
                    'critical': 2,
                    'major': 1,
                    'normal': 1,
                    'ok': 2,
                    'warning': 1
                },
                'statusCounts': {
                    'closed': 4,
                    'open': 4
                }
            }
        ])

        response = self.client.get('/environments?status=shelved')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('environments', data)
        self.assertCountEqual(data['environments'], [
            {
                'count': 0,
                'environment': 'Production',
                'severityCounts': {
                },
                'statusCounts': {
                }
            }
        ])

        # service
        response = self.client.get('/services')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('services', data)
        self.assertCountEqual(data['services'], [
            {
                'count': 8,
                'environment': 'Production',
                'service': 'Network',
                'severityCounts': {
                    'cleared': 1,
                    'critical': 2,
                    'major': 1,
                    'normal': 1,
                    'ok': 2,
                    'warning': 1
                },
                'statusCounts': {
                    'closed': 4,
                    'open': 4
                }
            },
            {
                'count': 2,
                'environment': 'Production',
                'service': 'Shared',
                'severityCounts': {
                    'critical': 1,
                    'major': 1
                },
                'statusCounts': {
                    'open': 2
                }
            }
        ])

        response = self.client.get('/services?status=ack')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('services', data)
        self.assertCountEqual(data['services'], [
            {
                'count': 0,
                'environment': 'Production',
                'service': 'Network',
                'severityCounts': {
                },
                'statusCounts': {
                }
            },
            {
                'count': 0,
                'environment': 'Production',
                'service': 'Shared',
                'severityCounts': {
                },
                'statusCounts': {
                }
            }
        ])

        # groups
        response = self.client.get('/alerts/groups')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('groups', data)
        self.assertCountEqual(data['groups'], [
            {
                'count': 1,
                'environment': 'Production',
                'group': 'Nw'
            },
            {
                'count': 1,
                'environment': 'Production',
                'group': 'nw'
            },
            {
                'count': 5,
                'environment': 'Production',
                'group': 'Network'
            },
            {
                'count': 1,
                'environment': 'Production',
                'group': 'net'
            }
        ])

        # tags
        response = self.client.get('/alerts/tags')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('tags', data)
        self.assertCountEqual(data['tags'], [
            {
                'count': 2,
                'environment': 'Production',
                'tag': 'bar'
            },
            {
                'count': 3,
                'environment': 'Production',
                'tag': 'quux'
            },
            {
                'count': 1,
                'environment': 'Production',
                'tag': 'baz'
            },
            {
                'count': 2,
                'environment': 'Production',
                'tag': 'foo'
            }
        ])
