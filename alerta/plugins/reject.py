import re

from alerta.plugins import PluginBase, RejectException

#  Modify this plug-in to suit your needs or disable it completely
#  by removing it from the list of PLUGINS in settings.py


ORIGIN_BLACKLIST = [
    re.compile('foo/bar'),
    re.compile('qux/.*')
]

ALLOWED_ENVIRONMENTS = [
    'Production',
    'Development'
]


class RejectPolicy(PluginBase):

    def pre_receive(self, alert):

        if any(regex.match(alert.origin) for regex in ORIGIN_BLACKLIST):
            raise RejectException("[POLICY] Alert origin '%s' has been blacklisted" % alert.origin)

        if alert.environment not in ALLOWED_ENVIRONMENTS:
            raise RejectException("[POLICY] Alert environment must be one of %s" % ', '.join(ALLOWED_ENVIRONMENTS))

        if not alert.service:
            raise RejectException("[POLICY] Alert must define a service")

        return alert

    def post_receive(self, alert):

        return
