import logging
import math

from alerta.app import alarm_model
from alerta.plugins import PluginBase
from alerta.models.enums import Severity

LOG = logging.getLogger('alerta.plugins')

escalate_map = {}
def Log2(x):
    if x == 0:
        return False

    return (math.log10(x) /
            math.log10(2))

def isPowerOfTwo(n):
    return (math.ceil(Log2(n)) ==
            math.floor(Log2(n)))

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

        if count > 1 and isPowerOfTwo(count):
            index = Log2(count) - 1
            if index > 4:
                index = 4
            alert.severity = escalate_map[index]
        return alert

    def status_change(self, alert, status, text, **kwargs):
        return

    def take_note(self, alert, text, **kwargs):
        raise NotImplementedError

    def take_action(self, alert, action, text, **kwargs):
        raise NotImplementedError
    
    def delete(self, alert, **kwargs) -> bool:
        raise NotImplementedError
