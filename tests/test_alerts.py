import json
import unittest
from datetime import datetime
from uuid import uuid4

from alerta.app import alarm_model, create_app, db, plugins
from alerta.models.alert import Alert
from alerta.plugins import PluginBase
from alerta.utils.api import process_alert


class AlertsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'ALERT_TIMEOUT': 120,
            'HISTORY_LIMIT': 5
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.resource = str(uuid4()).upper()[:8]

        self.fatal_alert = {
            'event': 'node_down',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network', 'Shared'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['foo'],
            'attributes': {'foo': 'abc def', 'bar': 1234, 'baz': False},
        }
        self.fatal_alert_no_attributes = {
            'event': 'node_down',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network', 'Shared'],
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
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 30
        }
        self.major_alert = {
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network', 'Shared'],
            'severity': 'major',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 40
        }
        self.warn_alert = {
            'event': 'node_marginal',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 50,
            'rawData': 'command output'
        }
        self.normal_alert = {
            'event': 'node_up',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'normal',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'timeout': 100
        }

        self.ok_alert = {
            'event': 'node_up',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'ok',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

        self.cleared_alert = {
            'event': 'node_up',
            'resource': self.resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'cleared',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

        self.ok2_alert = {
            'event': 'node_up',
            'resource': self.resource + '2',
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'ok',
            'correlate': ['node_down', 'node_marginal', 'node_up']
        }

        self.headers = {
            'Content-type': 'application/json',
            'X-Forwarded-For': '10.0.0.1'
        }

    def tearDown(self):
        db.destroy()

    def test_alert(self):

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], self.resource)
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['service'], ['Network', 'Shared'])
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')
        self.assertEqual(data['alert']['history'][0]['user'], None)

        alert_id = data['id']
        update_time = data['alert']['updateTime']

        # create duplicate alert
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['service'], ['Network', 'Shared'])
        self.assertEqual(data['alert']['duplicateCount'], 1)
        self.assertEqual(data['alert']['previousSeverity'], alarm_model.DEFAULT_PREVIOUS_SEVERITY)
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')
        self.assertEqual(data['alert']['updateTime'], update_time)

        # correlate alert (same event, diff sev)
        response = self.client.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['service'], ['Network'])
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['previousSeverity'], self.major_alert['severity'])
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')
        self.assertEqual(data['alert']['updateTime'], update_time)

        # de-duplicate
        response = self.client.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['service'], ['Network'])
        self.assertEqual(data['alert']['duplicateCount'], 1)
        self.assertEqual(data['alert']['trendIndication'], 'moreSevere')
        self.assertEqual(data['alert']['updateTime'], update_time)

        # correlate alert (diff event, same sev)
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['service'], ['Network', 'Shared'])
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['previousSeverity'], self.critical_alert['severity'])
        self.assertEqual(data['alert']['trendIndication'], 'noChange')
        self.assertEqual(data['alert']['updateTime'], update_time)

        # correlate alert (diff event, diff sev)
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['service'], ['Network', 'Shared'])
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['previousSeverity'], self.fatal_alert['severity'])
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')
        self.assertEqual(data['alert']['updateTime'], update_time)

        # correlate alert (diff event, diff sev)
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['service'], ['Network'])
        self.assertEqual(data['alert']['duplicateCount'], 0)
        self.assertEqual(data['alert']['previousSeverity'], self.major_alert['severity'])
        self.assertEqual(data['alert']['trendIndication'], 'lessSevere')
        self.assertEqual(data['alert']['updateTime'], data['alert']['receiveTime'])

        # get alert
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertIn(alert_id, data['alert']['id'])

        # delete alert
        response = self.client.delete('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)

    def test_alert_not_found(self):

        response = self.client.get('/alert/doesnotexist')
        self.assertEqual(response.status_code, 404)

    def test_get_alerts(self):

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        alert_id = data['id']

        response = self.client.get('/alerts')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertGreater(data['total'], 0)

        # delete alert
        response = self.client.delete('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)

    def test_alert_status(self):

        # create alert (status=open)
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        alert_id = data['id']
        update_time = data['alert']['updateTime']

        # severity != normal -> status=open
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['updateTime'], update_time)

        # ack alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'ack'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'ack')
        self.assertNotEqual(data['alert']['updateTime'], update_time)

        update_time = data['alert']['updateTime']

        # new severity > old severity -> status=open
        response = self.client.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')
        self.assertNotEqual(data['alert']['updateTime'], update_time)

        update_time = data['alert']['updateTime']

        # ack alert (again)
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'ack'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'ack')
        self.assertNotEqual(data['alert']['updateTime'], update_time)

        update_time = data['alert']['updateTime']

        # new severity <= old severity -> status=ack
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'ack')
        self.assertEqual(data['alert']['updateTime'], update_time)

        update_time = data['alert']['updateTime']

        # severity == normal -> status=closed
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertNotEqual(data['alert']['updateTime'], update_time)

        update_time = data['alert']['updateTime']

        # severity != normal -> status=open
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')
        self.assertNotEqual(data['alert']['updateTime'], update_time)

        update_time = data['alert']['updateTime']

        # severity = normal -> status=closed
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertNotEqual(data['alert']['updateTime'], update_time)

        # delete alert
        response = self.client.delete('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)

    def test_closed_alerts(self):

        # create normal alert (status=closed)
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['severity'], 'normal')
        self.assertEqual(data['alert']['duplicateCount'], 0)

        # update ok alert (status=closed)
        response = self.client.post('/alert', data=json.dumps(self.ok_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['severity'], 'ok')
        self.assertEqual(data['alert']['duplicateCount'], 0)

        # update cleared alert (status=closed)
        response = self.client.post('/alert', data=json.dumps(self.cleared_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['severity'], 'cleared')
        self.assertEqual(data['alert']['duplicateCount'], 0)

        # de-duplicate cleared alert (status=closed)
        response = self.client.post('/alert', data=json.dumps(self.cleared_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['severity'], 'cleared')
        self.assertEqual(data['alert']['duplicateCount'], 1)

    def test_expired_alerts(self):

        # create alert (status=open)
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        alert_id = data['id']

        # expire alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'expired'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'expired')

        # severity != normal -> status=open
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        # expire alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'expired'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'expired')

        # severity == normal -> status=closed
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # severity == warning -> status=open
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

    def test_reopen_alerts(self):

        # severity == warning -> status=open
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        alert_id = data['id']

        # severity == normal -> status=closed
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'normal')
        self.assertEqual(data['alert']['status'], 'closed')

        # severity == warning -> status=open
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['severity'], 'warning')
        self.assertEqual(data['alert']['duplicateCount'], 0)

        # operator=closed -> status=closed
        response = self.client.put('/alert/' + alert_id + '/action',
                                   data=json.dumps({'action': 'close', 'text': 'operator action'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['severity'], 'normal')
        self.assertEqual(data['alert']['status'], 'closed')

        # severity == warning -> status=open
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')
        self.assertEqual(data['alert']['severity'], 'warning')
        self.assertEqual(data['alert']['duplicateCount'], 0)

    def test_duplicate_status(self):

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)

        alert_id = data['id']

        # close alert
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'closed'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')

        # duplicate alert -> status=open
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

    def test_duplicate_value(self):

        # create alert (value=100)
        self.fatal_alert['value'] = '100'
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['duplicateCount'], 0)

        # duplicate alert (value=101)
        self.fatal_alert['value'] = '101'
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'open')

        # duplicate alert (value=102)
        self.fatal_alert['value'] = '102'
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual([h['value'] for h in data['alert']['history']], ['100', '101', '102'])

    def test_alert_tagging(self):

        # create alert
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['tags'], ['foo'])

        alert_id = data['id']

        # append tag to existing
        response = self.client.put('/alert/' + alert_id + '/tag',
                                   data=json.dumps({'tags': ['bar']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(sorted(data['alert']['tags']), ['bar', 'foo'])

        # duplicate tag is a no-op
        response = self.client.put('/alert/' + alert_id + '/tag',
                                   data=json.dumps({'tags': ['bar']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(sorted(data['alert']['tags']), ['bar', 'foo'])

        # delete tag
        response = self.client.put('/alert/' + alert_id + '/untag',
                                   data=json.dumps({'tags': ['foo']}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['tags'], ['bar'])

    def test_alert_no_attributes(self):

        plugins.plugins['remote_ip'] = DummyRemoteIPPlugin()

        # create alert with no attributes
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert_no_attributes), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['attributes'], {})

        alert_id = data['id']

        # ack alert, status change
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'ack'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'ack')
        self.assertEqual(data['alert']['attributes'], {})

        # close alert, action
        response = self.client.put('/alert/' + alert_id + '/action',
                                   data=json.dumps({'action': 'close'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['status'], 'closed')
        self.assertEqual(data['alert']['attributes'], {})

    def test_alert_attributes(self):

        # create alert with custom attributes
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(sorted(data['alert']['attributes']), sorted(
            {'foo': 'abc def', 'bar': 1234, 'baz': False, 'ip': '10.0.0.1'}))

        alert_id = data['id']

        # modify some attributes, add a new one and delete another
        response = self.client.put('/alert/' + alert_id + '/attributes', data=json.dumps(
            {'attributes': {'quux': ['q', 'u', 'u', 'x'], 'bar': None}}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(sorted(data['alert']['attributes']), sorted(
            {'foo': 'abc def', 'baz': False, 'quux': ['q', 'u', 'u', 'x'], 'ip': '10.0.0.1'}))

        # re-send duplicate alert with custom attributes ('quux' should not change)
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(sorted(data['alert']['attributes']), sorted(
            {'foo': 'abc def', 'bar': 1234, 'baz': False, 'quux': ['q', 'u', 'u', 'x'], 'ip': '10.0.0.1'}))

        # update custom attribute again (only 'quux' should change)
        response = self.client.put('/alert/' + alert_id + '/attributes',
                                   data=json.dumps({'attributes': {'quux': [1, 'u', 'u', 4]}}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(sorted(data['alert']['attributes']), sorted(
            {'foo': 'abc def', 'bar': 1234, 'baz': False, 'quux': [1, 'u', 'u', 4], 'ip': '10.0.0.1'}))

        # send correlated alert with custom attributes (nothing should change)
        response = self.client.post('/alert', data=json.dumps(self.critical_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        response = self.client.get('/alert/' + alert_id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(sorted(data['alert']['attributes']), sorted(
            {'foo': 'abc def', 'bar': 1234, 'baz': False, 'quux': [1, 'u', 'u', 4], 'ip': '10.0.0.1'}))

    def test_history_limit(self):

        # create alert (history change is dropped because length > limit)
        self.fatal_alert['value'] = '100'
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        alert_id = data['id']

        # duplicate alert, value change (history change is dropped because length > limit)
        self.fatal_alert['value'] = '101'
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # ack alert, status change
        response = self.client.put('/alert/' + alert_id + '/status',
                                   data=json.dumps({'status': 'ack'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # duplicate alert, value change
        self.fatal_alert['value'] = '102'
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # correlated alert, severity change
        self.major_alert['value'] = '99'
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # correlated alert, severity change
        self.fatal_alert['value'] = '104'
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)

        # duplicate alert, value change
        self.fatal_alert['value'] = '105'
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        self.assertListEqual([h['value'] for h in data['alert']['history']], ['101', '102', '99', '104', '105'])
        self.assertListEqual([h['type'] for h in data['alert']['history']],
                             ['status', 'value', 'severity', 'severity', 'value'])

    def test_timeout(self):

        # create alert with default timeout
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['timeout'], 120)

        # resend alert with different timeout
        self.fatal_alert['timeout'] = 20
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['timeout'], 20)

        # resend alert with timeout disabled (ie. 0)
        self.fatal_alert['timeout'] = 0
        response = self.client.post('/alert', data=json.dumps(self.fatal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['timeout'], 0)

        # send correlated with different timeout
        response = self.client.post('/alert', data=json.dumps(self.major_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['timeout'], 40)

        # send different correlated alert with different timeout
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['timeout'], 50)

        # send same correlated alert with different timeout
        self.warn_alert['timeout'] = 60
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['timeout'], 60)

        # send ok alert with default timeout
        response = self.client.post('/alert', data=json.dumps(self.ok_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['timeout'], 120)

    def test_query_param(self):
        # create alert
        response = self.client.post('/alert', data=json.dumps(self.normal_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        response = self.client.get('/alerts?q=event:node_up')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['alerts'][0]['event'], 'node_up')

    def test_alerts_show_fields(self):
        # create alert
        response = self.client.post('/alert', data=json.dumps(self.warn_alert), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        response = self.client.get('/alerts?show-raw-data=no')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alerts'][0]['rawData'], None)
        self.assertEqual(data['alerts'][0]['history'], [])

        response = self.client.get('/alerts?show-raw-data=yes&show-history=0')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alerts'][0]['rawData'], 'command output')
        self.assertEqual(data['alerts'][0]['history'], [])

        response = self.client.get('/alerts?show-history=yes')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['alerts'][0]['rawData'], None)
        self.assertEqual(len(data['alerts'][0]['history']), 1)

    def test_get_body(self):
        from flask import g
        with self.app.test_request_context('/'):
            g.login = 'foo'
            alert_in = Alert(
                resource='test1',
                event='event1',
                environment='Development',
                service=['svc1', 'svc2']
            )

            self.assertTrue(isinstance(alert_in.create_time, datetime))
            self.assertEqual(alert_in.last_receive_time, None)
            self.assertTrue(isinstance(alert_in.receive_time, datetime))
            self.assertEqual(alert_in.update_time, None)

            body = alert_in.get_body()
            self.assertEqual(type(body['createTime']), str)
            self.assertEqual(body['lastReceiveTime'], None)
            self.assertEqual(type(body['receiveTime']), str)
            self.assertEqual(body['updateTime'], None)

            alert_out = process_alert(alert_in)

            self.assertTrue(isinstance(alert_out.create_time, datetime))
            self.assertTrue(isinstance(alert_out.last_receive_time, datetime))
            self.assertTrue(isinstance(alert_out.receive_time, datetime))
            self.assertTrue(isinstance(alert_out.update_time, datetime))

            body = alert_out.get_body()
            self.assertEqual(type(body['createTime']), str)
            self.assertEqual(type(body['lastReceiveTime']), str)
            self.assertEqual(type(body['receiveTime']), str)
            self.assertEqual(type(body['updateTime']), str)


class DummyRemoteIPPlugin(PluginBase):

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        return alert

    def status_change(self, alert, status, text, **kwargs):
        return alert, status, text
