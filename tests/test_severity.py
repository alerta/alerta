import json
import unittest

from alerta.app import alarm_model, create_app, db
from alerta.models.alert import Alert
from alerta.utils.api import process_alert


class SeverityTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        correlate = ['node_down', 'node_marginal', 'node_up', 'node_pwned', 'node_trace']

        self.auth_alert = {
            'event': 'node_pwned',
            'resource': 'node1',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'security',
            'correlate': correlate,
            'tags': ['foo'],
            'attributes': {'foo': 'abc def', 'bar': 1234, 'baz': False}
        }
        self.critical_alert = {
            'event': 'node_down',
            'resource': 'node1',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': correlate
        }
        self.major_alert = {
            'event': 'node_marginal',
            'resource': 'node1',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'major',
            'correlate': correlate
        }
        self.warn_alert = {
            'event': 'node_marginal',
            'resource': 'node1',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'warning',
            'correlate': correlate
        }
        self.normal_alert = {
            'event': 'node_up',
            'resource': 'node1',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'normal',
            'correlate': correlate
        }

        self.trace_alert = {
            'event': 'node_trace',
            'resource': 'node1',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'trace',
            'correlate': correlate
        }

        self.ok_alert = {
            'event': 'node_ok',
            'resource': 'node2',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'ok',
            'correlate': []
        }

        self.inform_alert = {
            'event': 'node_inform',
            'resource': 'node3',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'informational',
            'correlate': []
        }

        self.debug_alert = {
            'event': 'node_debug',
            'resource': 'node4',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'debug',
            'correlate': []
        }

        self.headers = {
            'Content-type': 'application/json'
        }

    def tearDown(self):
        db.destroy()

    def test_inactive(self):

        # prevSev=(DEFAULT_PREVIOUS_SEVERITY=indeterminate), sev=ok, status=closed, trend=lessSevere
        response = self.client.post('/alert', data=json.dumps(self.ok_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['repeat'], False)
        self.assertEqual(data['alert']['previousSeverity'], alarm_model.DEFAULT_PREVIOUS_SEVERITY)
        self.assertEqual(data['alert']['severity'], 'ok')
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')

        # prevSev=(DEFAULT_PREVIOUS_SEVERITY=indeterminate), sev=informational, status=open, trend=lessSevere
        response = self.client.post('/alert', data=json.dumps(self.inform_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['repeat'], False)
        self.assertEqual(data['alert']['previousSeverity'], alarm_model.DEFAULT_PREVIOUS_SEVERITY)
        self.assertEqual(data['alert']['severity'], 'informational')
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')

        # prevSev=(DEFAULT_PREVIOUS_SEVERITY=indeterminate), sev=debug, status=open, trend=lessSevere
        response = self.client.post('/alert', data=json.dumps(self.debug_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['repeat'], False)
        self.assertEqual(data['alert']['previousSeverity'], alarm_model.DEFAULT_PREVIOUS_SEVERITY)
        self.assertEqual(data['alert']['severity'], 'debug')
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')

    def test_active(self):

        # prevSev=(DEFAULT_PREVIOUS_SEVERITY=indeterminate), sev=major, status=open, trend=moreSevere
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['repeat'], False)
        self.assertEqual(data['alert']['previousSeverity'], alarm_model.DEFAULT_PREVIOUS_SEVERITY)
        self.assertEqual(data['alert']['severity'], 'major')
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')

        alert_id = data['id']

        # ack alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'ack'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'ack')

        # prevSev=(DEFAULT_PREVIOUS_SEVERITY=indeterminate), sev=major, status=(current=ack), trend=moreSevere
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 1)
        self.assertEqual(data['alert']['repeat'], True)
        self.assertEqual(data['alert']['previousSeverity'], alarm_model.DEFAULT_PREVIOUS_SEVERITY)
        self.assertEqual(data['alert']['severity'], 'major')
        self.assertEqual(data['alert']['status'], 'ack')
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')

        # prevSev=major, sev=critical, status=open, trend=moreSevere
        response = self.client.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['repeat'], False)
        self.assertEqual(data['alert']['previousSeverity'], 'major')
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')

        # prevSev=major, sev=critical, status=(current=open), trend=moreSevere
        response = self.client.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 1)
        self.assertEqual(data['alert']['repeat'], True)
        self.assertEqual(data['alert']['previousSeverity'], 'major')
        self.assertEqual(data['alert']['severity'], 'critical')
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')

        # ack alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'ack'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'ack')

        # prevSev=critical, sev=warning, status=(current=ack), trend=lessSevere
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['repeat'], False)
        self.assertEqual(data['alert']['previousSeverity'], 'critical')
        self.assertEqual(data['alert']['severity'], 'warning')
        self.assertEqual(data['alert']['status'], 'ack')
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')

        # prevSev=warning, sev=normal, status=closed, trend=lessSevere
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['repeat'], False)
        self.assertEqual(data['alert']['previousSeverity'], 'warning')
        self.assertEqual(data['alert']['severity'], 'normal')
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')

        # prevSev=warning, sev=normal, status=closed, trend=lessSevere
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 1)
        self.assertEqual(data['alert']['repeat'], True)
        self.assertEqual(data['alert']['previousSeverity'], 'warning')
        self.assertEqual(data['alert']['severity'], 'normal')
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')

        # prevSev=normal, sev=trace, status=open, trend=lessSevere
        response = self.client.post('/alert', data=json.dumps(self.trace_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['repeat'], False)
        self.assertEqual(data['alert']['previousSeverity'], 'normal')
        self.assertEqual(data['alert']['severity'], 'trace')
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')

        # prevSev=trace, sev=security, status=open, trend=moreSevere
        response = self.client.post('/alert', data=json.dumps(self.auth_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['repeat'], False)
        self.assertEqual(data['alert']['previousSeverity'], 'trace')
        self.assertEqual(data['alert']['severity'], 'security')
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')

    def test_invalid(self):

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            with self.assertRaises(Exception) as e:
                process_alert(Alert(resource='foo', event='bar',
                                    environment='Development', service=['Svc'], severity='baz'))
            exc = e.exception
            self.assertEqual(str(exc)[:70], 'Severity (baz) is not one of security, critical, major, minor, warning')
