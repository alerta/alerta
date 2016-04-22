import re

from alerta.app import app
from alerta.plugins import PluginBase, RejectException


ORIGIN_BLACKLIST_REGEX = [re.compile(x) for x in app.config['ORIGIN_BLACKLIST']]


class RejectPolicy(PluginBase):

    def pre_receive(self, alert):
        if any(regex.match(alert.origin) for regex in ORIGIN_BLACKLIST_REGEX):
            raise RejectException("[POLICY] Alert origin '%s' has been blacklisted" % alert.origin)

        if alert.environment not in app.config['ALLOWED_ENVIRONMENTS']:
            raise RejectException("[POLICY] Alert environment must be one of %s" %
                                  ', '.join(app.config['ALLOWED_ENVIRONMENTS']))

        if not alert.service:
            raise RejectException("[POLICY] Alert must define a service")

        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return
