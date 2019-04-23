import abc
import logging
import os
from typing import Optional, TYPE_CHECKING, Any

from six import add_metaclass

if TYPE_CHECKING:
    from alerta.models.alert import Alert  # noqa

LOG = logging.getLogger('alerta.plugins')


@add_metaclass(abc.ABCMeta)
class PluginBase:

    def __init__(self, name=None):
        self.name = name or self.__module__
        if self.__doc__:
            LOG.info('\n{}\n'.format(self.__doc__))

        self.kwargs = {}

    @abc.abstractmethod
    def pre_receive(self, alert: 'Alert', **kwargs) -> 'Alert':
        """
        Pre-process an alert based on alert properties or reject it
        by raising RejectException or BlackoutPeriod.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def post_receive(self, alert: 'Alert', **kwargs) -> Optional['Alert']:
        """Send an alert to another service or notify users."""
        raise NotImplementedError

    @abc.abstractmethod
    def status_change(self, alert: 'Alert', status: str, text: str, **kwargs) -> Any:
        """Trigger integrations based on status changes."""
        raise NotImplementedError

    def take_action(self, alert: 'Alert', action: str, text: str, **kwargs) -> Any:
        """Trigger integrations based on external actions. (optional)"""
        raise NotImplementedError

    def get_config(self, key, default=None, type=None):

        if not self.kwargs:
            raise RuntimeError('Must initialize kwargs before calling get_config()')

        if key in os.environ:
            rv = os.environ[key]
            if type == list:
                return rv.split(',')
            elif type == bool:
                return rv.lower() in ['yes', 'true', 't', '1']
            elif type is not None:
                try:
                    rv = type(rv)
                except ValueError:
                    rv = default
            return rv

        return self.kwargs['config'].get(key, default)


class FakeApp:

    def init_app(self):
        from alerta.app import config
        self.config = config.get_user_config()


app = FakeApp()  # used for plugin config only (deprecated, use kwargs['config'])
