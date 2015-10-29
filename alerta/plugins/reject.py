import re

from alerta import settings
from alerta.plugins import PluginBase, RejectException


ORIGIN_BLACKLIST_REGEX = [re.compile(x) for x in settings.ORIGIN_BLACKLIST]


class RejectPolicy(PluginBase):

    def pre_receive(self, alert):

        if any(regex.match(alert.origin) for regex in ORIGIN_BLACKLIST_REGEX):
            raise RejectException("[POLICY] Alert origin '%s' has been blacklisted" % alert.origin)

        if alert.environment not in settings.ALLOWED_ENVIRONMENTS:
            raise RejectException("[POLICY] Alert environment must be one of %s" % ', '.join(settings.ALLOWED_ENVIRONMENTS))

        if not alert.service:
            raise RejectException("[POLICY] Alert must define a service")

        return alert

    def post_receive(self, alert):

        return
