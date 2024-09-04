import logging
import math

from alerta.models.alarms.alerta import SEVERITY_MAP
from alerta.models.enums import Severity
from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins')

escalate_map = {}


def Log2(x):
    if x == 0:
        return False

    return (math.log10(x)
            / math.log10(2))


def isPowerOfTwo(n):
    return (math.ceil(Log2(n))
            == math.floor(Log2(n)))


class AutoEscalateSeverity(PluginBase):
    """
    Increase the severity based on the Duplicate count
    """

    def __init__(self):
        # populate escalate severity map
        escalate_map[0] = Severity.Normal
        escalate_map[1] = Severity.Warning
        escalate_map[2] = Severity.Minor
        escalate_map[3] = Severity.Major
        escalate_map[4] = Severity.Critical

        super().__init__()

    def pre_receive(self, alert, **kwargs):
        return alert

    def post_receive(self, alert, **kwargs):
        count = alert.duplicate_count
        LOG.debug(f'Count: {count}')

        if count > 1 and isPowerOfTwo(count):
            index = int(Log2(count)) - 1

            if index > 4:
                index = 4

            currentseverity = alert.severity

            if SEVERITY_MAP[escalate_map[index]] < SEVERITY_MAP[currentseverity]:
                alert.severity = escalate_map[index]
                LOG.debug(f'index: {index}, currentseverity:{currentseverity}, new: {alert.severity}')

            if currentseverity != alert.severity:
                return alert, True
        return

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_note(self, alert, text, **kwargs):
        raise NotImplementedError

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError

    def delete(self, alert, **kwargs) -> bool:
        raise NotImplementedError
