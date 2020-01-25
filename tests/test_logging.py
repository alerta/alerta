import json
import unittest

from alerta.app import create_app, custom_webhooks
from alerta.models.alert import Alert
from alerta.webhooks import WebhookBase


class LoggingTestCase(unittest.TestCase):

    def setUp(self):

        test_config = {
            'TESTING': True,
            'AUTH_REQUIRED': False,
            'LOG_HANDLERS': ['console'],
            'LOG_FORMAT': 'verbose',
            'AUDIT_TRAIL': ['admin', 'write', 'auth'],
            'AUDIT_LOG': True
        }
        self.app = create_app(test_config)
        self.client = self.app.test_client()

    def test_custom_webhook(self):

        # setup custom webhook
        custom_webhooks.webhooks['json'] = DummyJsonWebhook()

        payload = """
            {"baz": "quux %X %%"}
        """

        # test json payload
        response = self.client.post('/webhooks/json?foo=bar', json=json.loads(payload), content_type='application/json')
        self.assertEqual(response.status_code, 201, response.data)
        data = json.loads(response.data.decode('utf-8'))
        self.assertEqual(data['alert']['resource'], 'bar')
        self.assertEqual(data['alert']['event'], 'quux %X %%')


class DummyJsonWebhook(WebhookBase):

    def incoming(self, query_string, payload):
        return Alert(
            resource=query_string['foo'],
            event=payload['baz'],
            environment='Production',
            service=['Foo']
        )
