
import abc
from typing import Optional, TYPE_CHECKING, Any

from six import add_metaclass

if TYPE_CHECKING:
    from alerta.models.alert import Alert  # noqa


@add_metaclass(abc.ABCMeta)
class PluginBase:

    def __init__(self, name=None):
        self.name = name or self.__module__

    @abc.abstractmethod
    def pre_receive(self, alert: 'Alert') -> 'Alert':
        """Pre-process an alert based on alert properties or reject it by raising RejectException."""
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


class FakeApp:

    def init_app(self):
        from alerta.app import config
        self.config = config.get_user_config()


app = FakeApp()  # used for plugin config only
