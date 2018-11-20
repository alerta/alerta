import logging
from typing import TYPE_CHECKING, Any, Optional

from alerta.models.alert import Alert
from alerta.plugins import PluginBase

if TYPE_CHECKING:
    from alerta.models.alert import Alert  # noqa

LOG = logging.getLogger('alerta.plugins.nbi')


class Prioritize(PluginBase):

    def __init__(self, name=None):
        super().__init__(name)

    def pre_receive(self, alert: 'Alert') -> 'Alert':

        PRIORITY = {
            ('critical', 'Production'): 'P1 HIGH',
            ('major', 'Production'): 'P1 HIGH',
            ('minor', 'Production'): 'P2 MEDIUM',
            ('warning', 'Production'): 'P2 MEDIUM',
            ('critical', 'Staging'): 'P1 HIGH',
            ('major', 'Staging'): 'P2 MEDIUM',
            ('minor', 'Staging'): 'P2 MEDIUM',
            ('warning', 'Staging'): 'P3 LOW',
            ('critical', 'Development'): 'P2 MEDIUM',
            ('major', 'Development'): 'P2 MEDIUM',
            ('minor', 'Development'): 'P3 LOW',
            ('warning', 'Development'): 'P3 LOW'
        }
        alert.attributes['priority'] = PRIORITY[(alert.severity, alert.environment)]
        return alert

    def post_receive(self, alert: 'Alert') -> Optional['Alert']:
        return

    def status_change(self, alert: 'Alert', status: str, text: str) -> Any:
        return

    def take_action(self, alert: 'Alert', action: str, text: str, **kwargs) -> Any:
        return
