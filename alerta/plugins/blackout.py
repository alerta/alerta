import logging
import os

from alerta.exceptions import BlackoutPeriod
from alerta.plugins import PluginBase, app

LOG = logging.getLogger('alerta.plugins')

NOTIFICATION_BLACKOUT = os.environ.get('NOTIFICATION_BLACKOUT') or app.config.get('NOTIFICATION_BLACKOUT', True)


class BlackoutHandler(PluginBase):
    """
    Default suppression blackout handler will drop alerts that match a blackout
    period and will return a 202 Accept HTTP status code.

    If "NOTIFICATION_BLACKOUT" is set to ``True`` then the alert is processed
    but alert status is set to "blackout" and the alert will not be passed to
    any plugins for further notification.
    """

    def pre_receive(self, alert):

        if app.config['ALARM_MODEL'] == 'ALERTA':
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

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError
