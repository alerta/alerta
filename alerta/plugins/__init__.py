import logging
import abc
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

    @abc.abstractmethod
    def pre_receive(self, alert: 'Alert') -> 'Alert':
        """
        Pre-process an alert based on alert properties or reject it
        by raising RejectException or BlackoutPeriod.
        """
        raise NotImplementedError

    def pre_dedup(self, alert: 'Alert', duplicate: 'Alert', **kwargs):
        raise NotImplementedError

    def deduped(self, alert: 'Alert', **kwargs):
        raise NotImplementedError

    def pre_update(self, alert: 'Alert', correlated: 'Alert', **kwargs):
        raise NotImplementedError

    def updated(self, alert: 'Alert', **kwargs):
        raise NotImplementedError

    def pre_create(self, alert: 'Alert', **kwargs):
        raise NotImplementedError

    def created(self, alert: 'Alert', **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def post_receive(self, alert: 'Alert') -> Optional['Alert']:
        """Send an alert to another service or notify users."""
        raise NotImplementedError

    @abc.abstractmethod
    def status_change(self, alert: 'Alert', status: str, text: str) -> Any:
        """Trigger integrations based on status changes."""
        raise NotImplementedError

    def take_action(self, alert: 'Alert', action: str, text: str, **kwargs) -> Any:
        """Trigger integrations based on external actions. (optional)"""
        raise NotImplementedError

    def pre_delete(self, alert: 'Alert', **kwargs):
        raise NotImplementedError

    def deleted(self, alert: 'Alert', **kwargs):
        raise NotImplementedError


class FakeApp:

    def init_app(self):
        from alerta.app import config
        self.config = config.get_user_config()


app = FakeApp()  # used for plugin config only
