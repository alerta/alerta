
import abc
import logging

from six import add_metaclass


LOG = logging.getLogger('alerta.actions')


@add_metaclass(abc.ABCMeta)
class ActionBase(object):

    def __init__(self, name=None):
        self.name = name or self.__module__

    @abc.abstractmethod
    def take_action(self, alert, action, text):
        """Trigger integrations based on actions eg. create issue."""
        return {}  # return dictionary of alert attributes


class FakeApp(object):

    def init_app(self):
        from alerta.app import config
        self.config = config.get_user_config()


app = FakeApp()  # used for plugin config only
