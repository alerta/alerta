import json
import unittest
from datetime import datetime
from uuid import uuid4

from alerta.app import create_app, db, plugins
from alerta.plugins import PluginBase

resource = str(uuid4()).upper()[:8]


class PluginsTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'PLUGINS': [],
            'PLUGINS_RAISE_ON_ERROR': True
        }

        self.app = create_app(test_config)
        self.client = self.app.test_client()

        self.reject_alert = {
            'id': '224040c5-5fdb-4d94-b564-398c755fdd02',
            'event': 'node_marginal',
            'resource': resource,
            'environment': 'Production',
            'service': [],  # alert will be rejected because service not defined
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['one', 'two']
        }

        self.accept_alert = {
            'id': '82d8379c-5ea2-45fa-92e0-51c69c3048b9',
            'event': 'node_marginal',
            'resource': resource,
            'environment': 'Production',
            'service': ['Network'],  # alert will be accepted because service defined
            'severity': 'warning',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'tags': ['three', 'four']
        }

        self.critical_alert = {
            'id': '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055',
            'event': 'node_down',
            'resource': resource,
            'environment': 'Production',
            'service': ['Network'],
            'severity': 'critical',
            'correlate': ['node_down', 'node_marginal', 'node_up'],
            'value': 'UP=0',
            'text': 'node is down.',
            'tags': ['cisco', 'core'],
            'attributes': {
                'region': 'EU',
                'site': 'london'
            },
            'origin': 'test_hooks.py',
            'rawData': 'raw text'

        }

        self.headers = {
            'Content-type': 'application/json'
        }

    def tearDown(self):
        plugins.plugins.clear()
        db.destroy()

    def test_run_hooks(self):

        plugins.plugins['plugin1'] = Plugin1()

        # create alert
        response = self.client.post('/alert', json=self.critical_alert, headers=self.headers)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data.decode('utf-8'))

        alert_id = data['id']

        # ack alert
        response = self.client.put('/alert/' + alert_id + '/action',
                                   data=json.dumps({'action': 'ack', 'text': 'ack text'}), headers=self.headers)
        self.assertEqual(response.status_code, 200)
        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # add note to alert
        note = {
            'text': 'this is a note'
        }
        response = self.client.put(f'/alert/{alert_id}/note', data=json.dumps(note), headers=self.headers)
        self.assertEqual(response.status_code, 201)
        response = self.client.get('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        # delete alert
        response = self.client.delete('/alert/' + alert_id, headers=self.headers)
        self.assertEqual(response.status_code, 200)


class Plugin1(unittest.TestCase, PluginBase):

    def pre_receive(self, alert, **kwargs):

        self.assertEqual(alert.id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.resource, resource)
        self.assertEqual(alert.event, 'node_down')
        self.assertEqual(alert.severity, 'critical')
        self.assertCountEqual(alert.correlate, ['node_down', 'node_marginal', 'node_up'])
        self.assertEqual(alert.status, 'open')
        self.assertCountEqual(alert.service, ['Network'])
        self.assertEqual(alert.group, 'Misc')
        self.assertEqual(alert.value, 'UP=0')
        self.assertEqual(alert.text, 'node is down.')
        self.assertCountEqual(alert.tags, ['cisco', 'core'])
        self.assertDictEqual(alert.attributes, {'region': 'EU', 'site': 'london'})
        self.assertEqual(alert.origin, 'test_hooks.py')
        self.assertEqual(alert.event_type, 'exceptionAlert')
        self.assertIsInstance(alert.create_time, datetime)
        self.assertEqual(alert.timeout, 86400)
        self.assertEqual(alert.raw_data, 'raw text')
        self.assertIsNone(alert.customer)

        self.assertIsNone(alert.duplicate_count)
        self.assertIsNone(alert.repeat)
        self.assertIsNone(alert.previous_severity)
        self.assertIsNone(alert.trend_indication)
        self.assertIsInstance(alert.receive_time, datetime)
        self.assertIsNone(alert.last_receive_id)
        self.assertIsNone(alert.last_receive_time)
        self.assertIsNone(alert.update_time)
        self.assertListEqual(alert.history, [])

        return alert

    def post_receive(self, alert, **kwargs):

        self.assertEqual(alert.id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.resource, resource)
        self.assertEqual(alert.event, 'node_down')
        self.assertEqual(alert.severity, 'critical')
        self.assertCountEqual(alert.correlate, ['node_down', 'node_marginal', 'node_up'])
        self.assertEqual(alert.status, 'open')
        self.assertCountEqual(alert.service, ['Network'])
        self.assertEqual(alert.group, 'Misc')
        self.assertEqual(alert.value, 'UP=0')
        self.assertEqual(alert.text, 'node is down.')
        self.assertCountEqual(alert.tags, ['cisco', 'core'])
        self.assertDictEqual(alert.attributes, {'region': 'EU', 'site': 'london'})
        self.assertEqual(alert.origin, 'test_hooks.py')
        self.assertEqual(alert.event_type, 'exceptionAlert')
        self.assertIsInstance(alert.create_time, datetime)
        self.assertEqual(alert.timeout, 86400)
        self.assertEqual(alert.raw_data, 'raw text')
        self.assertIsNone(alert.customer)

        self.assertEqual(alert.duplicate_count, 0)
        self.assertEqual(alert.repeat, False)
        self.assertEqual(alert.previous_severity, 'indeterminate')
        self.assertEqual(alert.trend_indication, 'moreSevere')
        self.assertIsInstance(alert.receive_time, datetime)
        self.assertEqual(alert.last_receive_id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertIsInstance(alert.last_receive_time, datetime)
        self.assertIsInstance(alert.update_time, datetime)

        self.assertEqual(alert.history[0].id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.history[0].event, 'node_down')
        self.assertEqual(alert.history[0].severity, 'critical')
        self.assertEqual(alert.history[0].status, 'open')
        self.assertEqual(alert.history[0].value, 'UP=0')
        self.assertEqual(alert.history[0].text, 'node is down.')
        self.assertEqual(alert.history[0].change_type, 'new')
        self.assertIsNone(alert.history[0].user)
        self.assertEqual(alert.history[0].timeout, 86400)

        return alert

    def take_action(self, alert, action, text, **kwargs):

        self.assertEqual(alert.id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.resource, resource)
        self.assertEqual(alert.event, 'node_down')
        self.assertEqual(alert.severity, 'critical')
        self.assertCountEqual(alert.correlate, ['node_down', 'node_marginal', 'node_up'])
        self.assertEqual(alert.status, 'open')
        self.assertCountEqual(alert.service, ['Network'])
        self.assertEqual(alert.group, 'Misc')
        self.assertEqual(alert.value, 'UP=0')
        self.assertEqual(alert.text, 'node is down.')
        self.assertCountEqual(alert.tags, ['cisco', 'core'])
        self.assertDictEqual(alert.attributes, {'region': 'EU', 'site': 'london'})
        self.assertEqual(alert.origin, 'test_hooks.py')
        self.assertEqual(alert.event_type, 'exceptionAlert')
        self.assertIsInstance(alert.create_time, datetime)
        self.assertEqual(alert.timeout, 86400)
        self.assertEqual(alert.raw_data, 'raw text')
        self.assertIsNone(alert.customer)

        self.assertEqual(alert.duplicate_count, 0)
        self.assertEqual(alert.repeat, False)
        self.assertEqual(alert.previous_severity, 'indeterminate')
        self.assertEqual(alert.trend_indication, 'moreSevere')
        self.assertIsInstance(alert.receive_time, datetime)
        self.assertEqual(alert.last_receive_id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertIsInstance(alert.last_receive_time, datetime)
        self.assertIsInstance(alert.update_time, datetime)

        self.assertEqual(alert.history[0].id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.history[0].event, 'node_down')
        self.assertEqual(alert.history[0].severity, 'critical')
        self.assertEqual(alert.history[0].status, 'open')
        self.assertEqual(alert.history[0].value, 'UP=0')
        self.assertEqual(alert.history[0].text, 'node is down.')
        self.assertEqual(alert.history[0].change_type, 'new')
        self.assertIsNone(alert.history[0].user)
        self.assertEqual(alert.history[0].timeout, 86400)

        self.assertEqual(action, 'ack')
        self.assertEqual(text, 'ack text')

        return alert, action, text

    def status_change(self, alert, status, text, **kwargs):

        self.assertEqual(alert.id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.resource, resource)
        self.assertEqual(alert.event, 'node_down')
        self.assertEqual(alert.severity, 'critical')
        self.assertCountEqual(alert.correlate, ['node_down', 'node_marginal', 'node_up'])
        self.assertEqual(alert.status, 'open')
        self.assertCountEqual(alert.service, ['Network'])
        self.assertEqual(alert.group, 'Misc')
        self.assertEqual(alert.value, 'UP=0')
        self.assertEqual(alert.text, 'node is down.')
        self.assertCountEqual(alert.tags, ['cisco', 'core'])
        self.assertDictEqual(alert.attributes, {'region': 'EU', 'site': 'london'})
        self.assertEqual(alert.origin, 'test_hooks.py')
        self.assertEqual(alert.event_type, 'exceptionAlert')
        self.assertIsInstance(alert.create_time, datetime)
        self.assertEqual(alert.timeout, 86400)
        self.assertEqual(alert.raw_data, 'raw text')
        self.assertIsNone(alert.customer)

        self.assertEqual(alert.duplicate_count, 0)
        self.assertEqual(alert.repeat, False)
        self.assertEqual(alert.previous_severity, 'indeterminate')
        self.assertEqual(alert.trend_indication, 'moreSevere')
        self.assertIsInstance(alert.receive_time, datetime)
        self.assertEqual(alert.last_receive_id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertIsInstance(alert.last_receive_time, datetime)
        self.assertIsInstance(alert.update_time, datetime)

        self.assertEqual(alert.history[0].id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.history[0].event, 'node_down')
        self.assertEqual(alert.history[0].severity, 'critical')
        self.assertEqual(alert.history[0].status, 'open')
        self.assertEqual(alert.history[0].value, 'UP=0')
        self.assertEqual(alert.history[0].text, 'node is down.')
        self.assertEqual(alert.history[0].change_type, 'new')
        self.assertIsNone(alert.history[0].user)
        self.assertEqual(alert.history[0].timeout, 86400)

        self.assertEqual(status, 'ack')
        self.assertEqual(text, 'ack text')

        return alert, status, text

    def take_note(self, alert, text, **kwargs):

        self.assertEqual(alert.id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.resource, resource)
        self.assertEqual(alert.event, 'node_down')
        self.assertEqual(alert.severity, 'critical')
        self.assertCountEqual(alert.correlate, ['node_down', 'node_marginal', 'node_up'])
        self.assertEqual(alert.status, 'ack')
        self.assertCountEqual(alert.service, ['Network'])
        self.assertEqual(alert.group, 'Misc')
        self.assertEqual(alert.value, 'UP=0')
        self.assertEqual(alert.text, 'node is down.')
        self.assertCountEqual(alert.tags, ['cisco', 'core'])
        self.assertDictEqual(alert.attributes, {'region': 'EU', 'site': 'london'})
        self.assertEqual(alert.origin, 'test_hooks.py')
        self.assertEqual(alert.event_type, 'exceptionAlert')
        self.assertIsInstance(alert.create_time, datetime)
        self.assertEqual(alert.timeout, 86400)
        self.assertEqual(alert.raw_data, 'raw text')
        self.assertIsNone(alert.customer)

        self.assertEqual(alert.duplicate_count, 0)
        self.assertEqual(alert.repeat, False)
        self.assertEqual(alert.previous_severity, 'indeterminate')
        self.assertEqual(alert.trend_indication, 'moreSevere')
        self.assertIsInstance(alert.receive_time, datetime)
        self.assertEqual(alert.last_receive_id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertIsInstance(alert.last_receive_time, datetime)
        self.assertIsInstance(alert.update_time, datetime)

        self.assertEqual(alert.history[0].id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.history[0].event, 'node_down')
        self.assertEqual(alert.history[0].severity, 'critical')
        self.assertEqual(alert.history[0].status, 'ack')
        self.assertEqual(alert.history[0].value, 'UP=0')
        self.assertEqual(alert.history[0].text, 'ack text')
        self.assertEqual(alert.history[0].change_type, 'ack')
        self.assertIsNone(alert.history[0].user)
        self.assertEqual(alert.history[0].timeout, 0)

        self.assertEqual(alert.history[1].id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.history[1].event, 'node_down')
        self.assertEqual(alert.history[1].severity, 'critical')
        self.assertEqual(alert.history[1].status, 'open')
        self.assertEqual(alert.history[1].value, 'UP=0')
        self.assertEqual(alert.history[1].text, 'node is down.')
        self.assertEqual(alert.history[1].change_type, 'new')
        self.assertIsNone(alert.history[1].user)
        self.assertEqual(alert.history[1].timeout, 86400)

        self.assertEqual(text, 'this is a note')

        return alert, text

    def delete(self, alert, **kwargs):

        self.assertEqual(alert.id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.resource, resource)
        self.assertEqual(alert.event, 'node_down')
        self.assertEqual(alert.severity, 'critical')
        self.assertCountEqual(alert.correlate, ['node_down', 'node_marginal', 'node_up'])
        self.assertEqual(alert.status, 'ack')
        self.assertCountEqual(alert.service, ['Network'])
        self.assertEqual(alert.group, 'Misc')
        self.assertEqual(alert.value, 'UP=0')
        self.assertEqual(alert.text, 'node is down.')
        self.assertCountEqual(alert.tags, ['cisco', 'core'])
        self.assertDictEqual(alert.attributes, {'region': 'EU', 'site': 'london'})
        self.assertEqual(alert.origin, 'test_hooks.py')
        self.assertEqual(alert.event_type, 'exceptionAlert')
        self.assertIsInstance(alert.create_time, datetime)
        self.assertEqual(alert.timeout, 86400)
        self.assertEqual(alert.raw_data, 'raw text')
        self.assertIsNone(alert.customer)

        self.assertEqual(alert.duplicate_count, 0)
        self.assertEqual(alert.repeat, False)
        self.assertEqual(alert.previous_severity, 'indeterminate')
        self.assertEqual(alert.trend_indication, 'moreSevere')
        self.assertIsInstance(alert.receive_time, datetime)
        self.assertEqual(alert.last_receive_id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertIsInstance(alert.last_receive_time, datetime)
        self.assertIsInstance(alert.update_time, datetime)

        # self.assertEqual(alert.history[0].id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.history[0].event, 'node_down')
        self.assertEqual(alert.history[0].severity, 'critical')
        self.assertEqual(alert.history[0].status, 'ack')
        self.assertEqual(alert.history[0].value, 'UP=0')
        self.assertEqual(alert.history[0].text, 'this is a note')
        self.assertEqual(alert.history[0].change_type, 'note')
        self.assertIsNone(alert.history[0].user)
        self.assertIsNone(alert.history[0].timeout)

        self.assertEqual(alert.history[1].id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.history[1].event, 'node_down')
        self.assertEqual(alert.history[1].severity, 'critical')
        self.assertEqual(alert.history[1].status, 'ack')
        self.assertEqual(alert.history[1].value, 'UP=0')
        self.assertEqual(alert.history[1].text, 'ack text')
        self.assertEqual(alert.history[1].change_type, 'ack')
        self.assertIsNone(alert.history[1].user)
        self.assertEqual(alert.history[1].timeout, 0)

        self.assertEqual(alert.history[2].id, '5e2f6e2f-01f9-4a56-b9c1-a4d8a412b055')
        self.assertEqual(alert.history[2].event, 'node_down')
        self.assertEqual(alert.history[2].severity, 'critical')
        self.assertEqual(alert.history[2].status, 'open')
        self.assertEqual(alert.history[2].value, 'UP=0')
        self.assertEqual(alert.history[2].text, 'node is down.')
        self.assertEqual(alert.history[2].change_type, 'new')
        self.assertIsNone(alert.history[2].user)
        self.assertEqual(alert.history[2].timeout, 86400)

        return True
