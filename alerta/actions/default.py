
from alerta.actions import app
from alerta.actions import ActionBase

from alerta.models import actions as action_code
from alerta.models import status_code


class UserActions(ActionBase):

    def take_action(self, alert, action, text):

        if action == action_code.ACTION_UNACK:
            alert.status = status_code.OPEN

        if action == action_code.ACTION_SHELVE:
            alert.status = status_code.SHELVED

        if action == action_code.ACTION_UNSHELVE:
            alert.status = status_code.OPEN

        if action == action_code.ACTION_ACK:
            alert.status = status_code.ACK

        if action == action_code.ACTION_CLOSE:
            alert.severity = app.config['DEFAULT_NORMAL_SEVERITY']
            alert.status = status_code.CLOSED

        return alert
