import logging

from alerta.exceptions import RateLimit
from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins.transient')

FLAPPING_WINDOW = 120  # seconds
FLAPPING_COUNT = 2  # threshold


class TransientAlert(PluginBase):

    def pre_receive(self, alert, **kwargs):
        LOG.info('Detecting transient alerts...')
        if alert.is_flapping(window=FLAPPING_WINDOW, count=FLAPPING_COUNT):
            raise RateLimit('Flapping alert received more than %s times in %s seconds' %
                            (FLAPPING_COUNT, FLAPPING_WINDOW))
        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return
