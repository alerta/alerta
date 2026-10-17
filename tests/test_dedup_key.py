import json
import unittest

from alerta.app import create_app, db, plugins
from alerta.models.enums import Scope
from alerta.models.key import ApiKey


class DedupKeyTestCase(unittest.TestCase):

    def create_app(self, **config):
        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': True,
            'CUSTOMER_VIEWS': True,
            'ADMIN_USERS': ['admin@alerta.io'],
            'ALLOWED_ENVIRONMENTS': ['Production', 'Development'],
            'PLUGINS': [],
        }
        test_config.update(config)
        self.app = create_app(test_config)
        self.client = self.app.test_client()

        with self.app.test_request_context('/'):
            self.app.preprocess_request()
            api_key = ApiKey(user='admin@alerta.io', scopes=[Scope.admin, Scope.read, Scope.write], text='admin-key')
            api_key.create()
        self.headers = {'Authorization': f'Key {api_key.key}', 'Content-type': 'application/json'}

    def setUp(self):
        self.create_app()

    def tearDown(self):
        plugins.plugins.clear()
        db.destroy()

    def send(self, expected_status=201, **fields):
        alert = {
            'resource': 'web01',
            'event': 'node_down',
            'environment': 'Production',
            'service': ['Web'],
            'severity': 'major',
        }
        alert.update(fields)
        response = self.client.post('/alert', data=json.dumps(alert), headers=self.headers)
        self.assertEqual(response.status_code, expected_status, response.data)
        return json.loads(response.data.decode('utf-8')).get('alert')

    def test_template_key_is_returned(self):
        alert = self.send()

        self.assertEqual(alert['dedupKey'], '["web01", "node_down"]')
        self.assertEqual(alert['keySource'], 'template')

    def test_sender_key_deduplicates_across_resource_and_event(self):
        first = self.send(resource='web01', event='node_down', dedupKey='incident-42')
        second = self.send(resource='web02', event='node_unreachable', dedupKey='incident-42')

        self.assertEqual(first['keySource'], 'sender')
        self.assertEqual(second['id'], first['id'])
        self.assertEqual(second['duplicateCount'], 1)
        self.assertEqual((second['resource'], second['event']), ('web02', 'node_unreachable'))

    def test_sender_key_severity_change_correlates(self):
        first = self.send(dedupKey='incident-42', severity='major')
        second = self.send(dedupKey='incident-42', severity='critical')

        self.assertEqual(second['id'], first['id'])
        self.assertEqual(second['severity'], 'critical')
        self.assertEqual(second['previousSeverity'], 'major')

    def test_sender_key_never_matches_template_key(self):
        template = self.send()
        sender = self.send(dedupKey=template['dedupKey'])

        self.assertNotEqual(sender['id'], template['id'])
        self.assertEqual(sender['dedupKey'], template['dedupKey'])

    def test_same_key_in_another_environment_is_a_new_alert(self):
        prod = self.send(dedupKey='incident-42', environment='Production')
        dev = self.send(dedupKey='incident-42', environment='Development')

        self.assertNotEqual(dev['id'], prod['id'])

    def test_same_key_for_another_customer_is_a_new_alert(self):
        acme = self.send(dedupKey='incident-42', customer='acme')
        other = self.send(dedupKey='incident-42', customer='other')
        acme_again = self.send(dedupKey='incident-42', customer='acme')

        self.assertNotEqual(other['id'], acme['id'])
        self.assertEqual(acme_again['id'], acme['id'])

    def test_invalid_sender_key_is_rejected(self):
        for value in ['', 'x' * 256, 42, ['incident-42']]:
            with self.subTest(dedupKey=value):
                self.send(expected_status=400, dedupKey=value)

    def test_sender_key_at_max_length_is_accepted(self):
        alert = self.send(dedupKey='x' * 255)

        self.assertEqual(alert['dedupKey'], 'x' * 255)

    def test_template_from_attributes(self):
        self.create_app(DEDUP_KEY_FIELDS=['attributes.instanceId', 'event'])

        first = self.send(resource='10.0.0.1', attributes={'instanceId': 'i-123'})
        second = self.send(resource='10.0.0.2', attributes={'instanceId': 'i-123'})
        other = self.send(resource='10.0.0.1', attributes={'instanceId': 'i-456'})

        self.assertEqual(first['dedupKey'], '["i-123", "node_down"]')
        self.assertEqual(second['id'], first['id'])
        self.assertEqual(second['resource'], '10.0.0.2')
        self.assertNotEqual(other['id'], first['id'])

    def test_template_correlate_list_uses_key_without_event(self):
        self.create_app(DEDUP_KEY_FIELDS=['attributes.instanceId', 'event'])
        correlate = ['node_down', 'node_up']

        down = self.send(resource='10.0.0.1', event='node_down', correlate=correlate, attributes={'instanceId': 'i-123'})
        up = self.send(resource='10.0.0.2', event='node_up', severity='normal', correlate=correlate, attributes={'instanceId': 'i-123'})

        self.assertEqual(up['id'], down['id'])
        self.assertEqual(up['event'], 'node_up')
        self.assertEqual(up['dedupKey'], '["i-123", "node_up"]')

    def test_template_without_event_ignores_correlate_list(self):
        self.create_app(DEDUP_KEY_FIELDS=['resource'])

        down = self.send(event='node_down', correlate=['node_down', 'node_up'])
        disk = self.send(event='disk_full')

        self.assertEqual(disk['id'], down['id'])
        self.assertEqual(disk['event'], 'disk_full')

    def action(self, alert, action):
        response = self.client.put(f"/alert/{alert['id']}/action", data=json.dumps({'action': action}), headers=self.headers)
        self.assertEqual(response.status_code, 200, response.data)
        response = self.client.get(f"/alert/{alert['id']}", headers=self.headers)
        return json.loads(response.data.decode('utf-8'))['alert']

    def test_template_change_does_not_rekey_stored_alerts(self):
        alert = self.send()
        self.action(alert, 'ack')
        self.create_app(DEDUP_KEY_FIELDS=['resource'])

        alert = self.action(alert, 'unack')

        self.assertEqual(alert['status'], 'open')
        self.assertEqual(alert['dedupKey'], '["web01", "node_down"]')

    def test_sender_key_alert_unack_restores_status(self):
        alert = self.send(dedupKey='incident-42')
        self.action(alert, 'ack')

        self.assertEqual(self.action(alert, 'unack')['status'], 'open')

    def test_invalid_template_fails_at_startup(self):
        for fields in [[], ['environment'], ['customer'], ['attributes.'], ['resource', 'resource']]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                create_app({'TESTING': True, 'DEDUP_KEY_FIELDS': fields})
