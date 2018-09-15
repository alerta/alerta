import logging

from alerta.exceptions import BlackoutPeriod
from alerta.plugins import PluginBase

try:
    from alerta.plugins import app  # alerta >= 5.0
except ImportError:
    from alerta.app import app  # type: ignore # alerta < 5.0


LOG = logging.getLogger('alerta.plugins.blackout')


class BlackoutHandler(PluginBase):
    """
    Default suppression blackout handler will drop alerts that match a blackout
    period and will return a 202 Accept HTTP status code.

    If "NOTIFICATION_BLACKOUT" is set to ``True`` then the alert is processed
    but alert status is set to "blackout" and the alert will not be passed to
    any plugins for further notification.
    """

    def pre_receive(self, alert):

        if alert.is_blackout():
            if app.config.get('NOTIFICATION_BLACKOUT', True):
                LOG.debug('Set status to "blackout" during blackout period (id=%s)' % alert.id)
                alert.status = 'blackout'
            else:
                LOG.debug('Suppressed alert during blackout period (id=%s)' % alert.id)
                raise BlackoutPeriod('Suppressed alert during blackout period')
        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return
