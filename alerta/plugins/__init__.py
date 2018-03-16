
import abc
import logging

from six import add_metaclass


LOG = logging.getLogger('alerta.plugins')


@add_metaclass(abc.ABCMeta)
class PluginBase(object):

    def __init__(self, name=None):
        self.name = name or self.__module__

    @abc.abstractmethod
    def pre_receive(self, alert):
        """Pre-process an alert based on alert properties or reject it by raising RejectException."""
        return alert

    @abc.abstractmethod
    def post_receive(self, alert):
        """Send an alert to another service or notify users."""
        return None

    @abc.abstractmethod
    def status_change(self, alert, status, text):
        """Trigger integrations based on status changes."""
        return None


class FakeApp(object):

    def init_app(self):
        from alerta.app import config
        self.config = config.get_user_config()


app = FakeApp()  # used for plugin config only
