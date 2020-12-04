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
        HEARTBEAT_EVENTS = self.get_config('HEARTBEAT_EVENTS', default=['Heartbeat'], type=list, **kwargs)

        if alert.event in HEARTBEAT_EVENTS:
            hb = Heartbeat(
                origin=alert.origin,
                tags=alert.tags,
                attributes={
                    'environment': alert.environment,
                    'severity': alert.severity,
                    'service': alert.service,
                    'group': alert.group
                },
                timeout=alert.timeout,
                customer=alert.customer
            )
            r = hb.create()
            raise HeartbeatReceived(r.id)

        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError

    def delete(self, alert, **kwargs) -> bool:
        raise NotImplementedError
