import logging

try:
    from alerta.plugins import app  # alerta >= 5.0
except ImportError:
    from alerta.app import app  # alerta < 5.0

from alerta.exceptions import BlackoutPeriod
from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins.blackout')


class BlackoutHandler(PluginBase):
    """
    Default blackout handler suppresses alerts that match a blackout period and
    returns a 202 Accept status code.

    If "NOTIFICATION_BLACKOUT=True" is set then the alert is processed as normal but
    an attribute "notify=False" is added to the alert. It is up to downstream
    notification integrations (plugins) to check for this notification suppression.
    """
    def pre_receive(self, alert):

        is_blackout = alert.is_blackout()
        do_not_notify = app.config.get('NOTIFICATION_BLACKOUT', False)

        if do_not_notify and is_blackout:
            LOG.debug('Suppressed notifications during blackout period (id=%s)' % alert.id)
            alert.attributes['notify'] = False
        elif do_not_notify and not is_blackout:
            alert.attributes['notify'] = True
        elif not do_not_notify and is_blackout:
            LOG.debug('Suppressed alert during blackout period (id=%s)' % alert.id)
            raise BlackoutPeriod("Suppressed alert during blackout period")
        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return
