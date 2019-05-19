import logging

from flask import g

from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins')


class AckedBy(PluginBase):
    """
    Add "acked-by" attribute to alerts when an operator acknowledges alert and
    unset the attribute when alert is unacknowledged. To display the current
    value in the alert summary add "acked-by" to the COLUMNS server setting.
    """

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        return

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_action(self, alert, action, text, **kwargs):

        if action == 'ack':
            alert.attributes['acked-by'] = g.login
        if action == 'unack':
            alert.attributes['acked-by'] = None
        return alert
