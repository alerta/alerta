import logging

from alerta.exceptions import BlackoutPeriod
from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins')


class BlackoutHandler(PluginBase):
    """
    Default suppression blackout handler will drop alerts that match a blackout
    period and will return a 202 Accept HTTP status code.

    If "NOTIFICATION_BLACKOUT" is set to ``True`` then the alert is processed
    but alert status is set to "blackout" and the alert will not be passed to
    any plugins for further notification.
    """

    def pre_receive(self, alert, **kwargs):
        NOTIFICATION_BLACKOUT = self.get_config('NOTIFICATION_BLACKOUT', default=True, type=bool, **kwargs)

        if self.get_config('ALARM_MODEL', **kwargs) == 'ALERTA':
            status = 'blackout'
        else:
            status = 'OOSRV'  # ISA_18_2

        if alert.is_blackout():
            if NOTIFICATION_BLACKOUT:
                LOG.debug('Set status to "{}" during blackout period (id={})'.format(status, alert.id))
                alert.status = status
            else:
                LOG.debug('Suppressed alert during blackout period (id={})'.format(alert.id))
                raise BlackoutPeriod('Suppressed alert during blackout period')
        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError
