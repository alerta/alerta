
from alerta.plugins import PluginBase, RejectException


class NormaliseAlert(PluginBase):

    def pre_receive(self, alert):

        alert.text = '%s: %s' % (alert.severity.upper(), alert.text)

        return alert

    def post_receive(self, alert):

        return