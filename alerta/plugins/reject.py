import logging
import re

from alerta.exceptions import RejectException
from alerta.plugins import PluginBase, app

LOG = logging.getLogger('alerta.plugins.reject')

ORIGIN_BLACKLIST_REGEX = [re.compile(x) for x in app.config['ORIGIN_BLACKLIST']]
ALLOWED_ENVIRONMENT_REGEX = [re.compile(x) for x in app.config['ALLOWED_ENVIRONMENTS']]
ALLOWED_ENVIRONMENTS = app.config.get('ALLOWED_ENVIRONMENTS', [])


class RejectPolicy(PluginBase):
    """
    Default reject policy will block alerts that do not have the following
    required attributes:
    1) environment - must match an allowed environment. By default it should
       be either "Production" or "Development". Config setting is `ALLOWED_ENVIRONMENTS`.
    2) service - must supply a value for service. Any value is acceptable.
    """

    def pre_receive(self, alert):

        if any(regex.match(alert.origin) for regex in ORIGIN_BLACKLIST_REGEX):
            LOG.warning("[POLICY] Alert origin '%s' has been blacklisted", alert.origin)
            raise RejectException("[POLICY] Alert origin '%s' has been blacklisted" % alert.origin)

        if not any(regex.match(alert.environment) for regex in ALLOWED_ENVIRONMENT_REGEX):
            LOG.warning('[POLICY] Alert environment does not match one of %s', ', '.join(ALLOWED_ENVIRONMENTS))
            raise RejectException('[POLICY] Alert environment does not match one of %s' %
                                  ', '.join(ALLOWED_ENVIRONMENTS))

        if not alert.service:
            LOG.warning('[POLICY] Alert must define a service')
            raise RejectException('[POLICY] Alert must define a service')

        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return
