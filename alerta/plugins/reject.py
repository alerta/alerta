import re
import logging

from alerta.app import app
from alerta.app.exceptions import RejectException
from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins.reject')

ORIGIN_BLACKLIST_REGEX = [re.compile(x) for x in app.config['ORIGIN_BLACKLIST']]
ALLOWED_ENVIRONMENTS = app.config.get('ALLOWED_ENVIRONMENTS', [])

class RejectPolicy(PluginBase):

    def pre_receive(self, alert):
        if any(regex.match(alert.origin) for regex in ORIGIN_BLACKLIST_REGEX):
            LOG.warning("[POLICY] Alert origin '%s' has been blacklisted" % alert.origin)
            raise RejectException("[POLICY] Alert origin '%s' has been blacklisted" % alert.origin)

        if alert.environment not in ALLOWED_ENVIRONMENTS:
            LOG.warning("[POLICY] Alert environment must be one of %s" % ', '.join(ALLOWED_ENVIRONMENTS))
            raise RejectException("[POLICY] Alert environment must be one of %s" % ', '.join(ALLOWED_ENVIRONMENTS))

        if not alert.service:
            LOG.warning("[POLICY] Alert must define a service")
            raise RejectException("[POLICY] Alert must define a service")

        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return
