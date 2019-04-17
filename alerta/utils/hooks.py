import blinker
from flask import Flask

from alerta.exceptions import ApiError, RejectException

hook_signals = blinker.Namespace()

pre_receive_hook = hook_signals.signal('pre-receive')
post_receive_hook = hook_signals.signal('post-receive')
status_change_hook = hook_signals.signal('status-change')
take_action_hook = hook_signals.signal('take-action')


class HookTrigger:

    def __init__(self, app: Flask=None) -> None:
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        pre_receive_hook.connect(self.process_pre_receive)
        post_receive_hook.connect(self.process_post_receive)
        status_change_hook.connect(self.process_status_change)
        take_action_hook.connect(self.process_take_action)

    def process_pre_receive(self, alert):
        # not used
        pass

    def process_post_receive(self, alert):
        # not used
        pass

    def process_status_change(self, alert, status, text):
        from alerta.utils.api import process_status
        try:
            alert, status, text = process_status(alert, status, text)
        except RejectException as e:
            raise ApiError(str(e), 400)
        except Exception as e:
            raise ApiError(str(e), 500)

        alert.tag(alert.tags)
        alert.update_attributes(alert.attributes)

        return alert, status, text

    def process_take_action(self, alert, action, text):
        # not used
        pass
