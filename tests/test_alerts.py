import json
import unittest

from uuid import uuid4
from alerta.app import app


class AlertTestCase(unittest.TestCase):

    def setUp(self):

        app.config['TESTING'] = True
        app.config['AUTH_REQUIRED'] = False
        self.app = app.test_client()

        self.resource = str(uuid4()).upper()[:8]

        self.fatal_alert = {
            'event': 'node_down',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo']
        }
        self.critical_alert = {
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }
        self.major_alert = {
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }
        self.warn_alert = {
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }
        self.normal_alert = {
            'event': 'node_up',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'normal',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

        self.headers = {
            'Content-type': 'application/json'
        }

    def tearDown(self):

        pass

    def test_debug_output(self):

        response = self.app.get('/_')
        self.assertEqual(response.status_code, 200)
        self.assertIn("ok", response.data.decode('utf-8'))

    def test_alert(self):

        # create alert
        response = self.app.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], self.resource)
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')

        alert_id = data['id']

        # create duplicate alert
        response = self.app.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['duplicateCount'], 1)
        self.assertEqual(data['alert']['previousSeverity'], 'unknown')
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')

        # correlate alert (same event, diff sev)
        response = self.app.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['previousSeverity'], self.major_alert['severity'])
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')


        # de-duplicate
        response = self.app.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['duplicateCount'], 1)
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')

        # correlate alert (diff event, same sev)
        response = self.app.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['previousSeverity'], self.critical_alert['severity'])
        self.assertEqual(data['alert']['trendIndication'], 'noChange')


        # correlate alert (diff event, diff sev)
        response = self.app.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['previousSeverity'], self.fatal_alert['severity'])
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')

        # correlate alert (diff event, diff sev)
        response = self.app.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['previousSeverity'], self.major_alert['severity'])
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')

        # get alert
        response = self.app.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])

        # delete alert
        response = self.app.delete('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)

    def test_alert_not_found(self):

        response = self.app.get('/alert/doesnotexist')
        self.assertEqual(response.status_code, 404)

    def test_get_alerts(self):

        # create alert
        response = self.app.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        alert_id = data['id']

        response = self.app.get('/alerts')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertGreater(data['total'], 0)

        # delete alert
        response = self.app.delete('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)

    def test_alert_status(self):

        # create alert (status=open)
        response = self.app.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        alert_id = data['id']

        # severity != normal -> status=open
        response = self.app.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        # ack alert
        response = self.app.post('/alert/' + alert_id + '/status', data=json.dumps({'status': 'ack'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.app.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'ack')

        # new severity > old severity -> status=open
        response = self.app.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        # ack alert (again)
        response = self.app.post('/alert/' + alert_id + '/status', data=json.dumps({'status': 'ack'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.app.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'ack')

        # new severity <= old severity -> status=ack
        response = self.app.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'ack')

        # severity == normal -> status=closed
        response = self.app.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # severity != normal -> status=open
        response = self.app.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        # severity = normal -> status=closed
        response = self.app.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # delete alert
        response = self.app.delete('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)

    def test_expired_alerts(self):

        # create alert (status=open)
        response = self.app.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        alert_id = data['id']

        # expire alert
        response = self.app.post('/alert/' + alert_id + '/status', data=json.dumps({'status': 'expired'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.app.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'expired')

        # severity != normal -> status=open
        response = self.app.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        # expire alert
        response = self.app.post('/alert/' + alert_id + '/status', data=json.dumps({'status': 'expired'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.app.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'expired')

        # severity == normal -> status=closed
        response = self.app.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # severity == warning -> status=open
        response = self.app.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

    def test_duplicate_status(self):

        # create alert
        response = self.app.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)

        alert_id = data['id']

        # close alert
        response = self.app.post('/alert/' + alert_id + '/status', data=json.dumps({'status': 'closed'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.app.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], "closed")

        # duplicate alert -> status=open
        response = self.app.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

    def test_alert_tagging(self):

        # create alert
        response = self.app.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['tags'], ['foo'])

        alert_id = data['id']

        # append tag to existing
        response = self.app.post('/alert/' + alert_id + '/tag', data=json.dumps({'tags': ['bar']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.app.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['tags'], ['foo', 'bar'])

        # duplicate tag is a no-op
        response = self.app.post('/alert/' + alert_id + '/tag', data=json.dumps({'tags': ['bar']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.app.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['tags'], ['foo', 'bar'])

        # delete tag
        response = self.app.post('/alert/' + alert_id + '/untag', data=json.dumps({'tags': ['foo']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.app.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['tags'], ['bar'])

    def test_aggregations(self):

        # counts
        response = self.app.get('/alerts/count')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('statusCounts', data)
        self.assertIn('severityCounts', data)

        # top10
        response = self.app.get('/alerts/top10')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('top10', data)

        # environments
        response = self.app.get('/environments')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('environments', data)

        # service
        response = self.app.get('/services')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn('services', data)
