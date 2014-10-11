import re

from alerta.plugins import PluginBase, RejectException

ORIGIN_BLACKLIST = [
    re.compile('foo/bar'),
    re.compile('qux/.*')
]


class RejectPolicy(PluginBase):

    def pre_receive(self, alert):

        if any(regex.match(alert.origin) for regex in ORIGIN_BLACKLIST):
            raise RejectException("[POLICY] Alert origin '%s' has been blacklisted" % alert.origin)

        if alert.environment not in ['Production', 'Development']:
            raise RejectException("[POLICY] Alert with unsupported environment '%s' rejected" % alert.environment)

        if not alert.service:
            raise RejectException("[POLICY] Alert must define a service")

        return alert

    def post_receive(self, alert):

        pass
