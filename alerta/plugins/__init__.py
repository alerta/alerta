import abc
import logging
import os
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from alerta.models.alert import Alert  # noqa

LOG = logging.getLogger('alerta.plugins')


class PluginBase(metaclass=abc.ABCMeta):

    def __init__(self, name=None):
        self.name = name or self.__module__
        if self.__doc__:
            LOG.info(f'\n{self.__doc__}\n')

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

    def take_note(self, alert: 'Alert', text: Optional[str], **kwargs) -> Any:
        """Trigger integrations based on notes. (optional)"""
        raise NotImplementedError

    def delete(self, alert: 'Alert', **kwargs) -> bool:
        """Trigger integrations when an alert is deleted. (optional)"""
        raise NotImplementedError

    @staticmethod
    def get_config(key, default=None, type=None, **kwargs):

        if key in os.environ:
            rv = os.environ[key]
            if type == bool:
                return rv.lower() in ['yes', 'on', 'true', 't', '1']
            elif type == list:
                return rv.split(',')
            elif type is not None:
                try:
                    rv = type(rv)
                except ValueError:
                    rv = default
            return rv

        try:
            rv = kwargs['config'].get(key, default)
        except KeyError:
            rv = default
        return rv


class FakeApp:

    def init_app(self):
        from alerta.app import config
        self.config = config.get_user_config()


app = FakeApp()  # used for plugin config only (deprecated, use kwargs['config'] or get_config(..., **kwargs))
