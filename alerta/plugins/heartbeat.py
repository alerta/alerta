import logging

from alerta.exceptions import HeartbeatReceived
from alerta.models.heartbeat import Heartbeat
from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins')


class HeartbeatReceiver(PluginBase):
    """
    Default heartbeat receiver intercepts alerts with event='Heartbeat', converts
    them into heartbeats and will return a 202 Accept HTTP status code.
    """

    def pre_receive(self, alert, **kwargs):

        if alert.event == 'Heartbeat':
            hb = Heartbeat(
                origin=alert.origin,
                tags=alert.tags,
                timeout=alert.timeout,
                customer=alert.customer
            )
            hb.create()
            raise HeartbeatReceived('Alert converted to heartbeat')

        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError
