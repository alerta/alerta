"""
Alarm states and transition paths.

See ANSI/ISA 18.2 Management of Alarm Systems for the Process Industries
https://www.isa.org/store/ansi/isa-182-2016/46962105

"""

from alerta.app import severity
from alerta.models import severity_code
# from alerta.models import status_code


## XXX may need to automatically ACK RTN_UNACK alerts based on timeout

NORMAL = 'Normal'
UNACK = 'Unack'
ACK = 'Ack'
RTN_UNACK = 'RTN Unack'
LATCHED_UNACK = 'Latch Unack'
LATCHED_ACK = 'Latch Ack'
SHELVED = 'Shelved'
SUPP_BY_DESIGN = 'Supp. by Design' # not used?
OUT_OF_SERVICE = 'Out-of-Service'  # Blackout
UNKNOWN = 'Unknown'
INVALID = 'Invalid'

ACTION_ACK = 'ack'
ACTION_RESET = 'reset'
ACTION_SHELVE = 'shelve'
ACTION_UNSHELVE = 'unshelve'


def transition(previous_severity, current_severity, state=NORMAL, latched=False, action=None):
    # Alarm Occurs, Normal (A) -> Unack (B)
    if state == NORMAL:
        if current_severity in severity_code.NOT_OK:
            return UNACK
    # Operator Ack, Unack (B) -> Ack (C)
    if state == UNACK:
        if action == ACTION_ACK:
            return ACK
    # Re-Alarm, Ack (C) -> Unack (B)
    if state == ACK:
        if severity.trend(previous_severity, current_severity) == severity_code.MORE_SEVERE:
            return UNACK
    # Process RTN Alarm Clears, Ack (C) -> Normal (A)
    if state == ACK and not latched:
        if current_severity in severity_code.ALL_OK:
            return NORMAL
    # Process RTN Latched Alarm, Ack (C) -> Latch Ack (F)
    if state == ACK and latched:
        if current_severity in severity_code.ALL_OK:
            return LATCHED_ACK
    # Process RTN and Alarm Clears, Unack (B) -> RTN Unack (D)
    if state == UNACK and not latched:
        if current_severity in severity_code.ALL_OK:
            return RTN_UNACK
    # Process RTN, Unack (B) -> Latch Unack (E)
    if state == UNACK and latched:
        if current_severity in severity_code.ALL_OK:
            return LATCHED_UNACK
    # Operator Ack, RTN Unack (D) -> Normal (A)
    if state == RTN_UNACK:
        if action == ACTION_ACK:
            return NORMAL
    # Re-Alarm Unack, RTN Unack (D) -> Unack (B)  # XXX - missing from descriptions?
    if state == RTN_UNACK:
        if current_severity in severity_code.NOT_OK:
            return UNACK
    # Operator Resets, Latch Unack (E) -> RTN Unack (D)
    if state == LATCHED_UNACK:
        if action == ACTION_RESET:
            return RTN_UNACK
    # Operator Ack, Latch Unack (E) -> Latch Ack (F)
    if state == LATCHED_UNACK:
        if action == ACTION_ACK:
            return LATCHED_ACK
    # Operator Resets, Latch Ack (F) -> Normal (A)
    if state == LATCHED_ACK:
        if action == ACTION_RESET:
            return NORMAL
    # Shelve (Any->G)
    if action == ACTION_SHELVE:
        return SHELVED
    # Unshelve (G->Any)
    if action == ACTION_UNSHELVE:
        return UNACK
    # Designed Suppression (Any->H)

    # Designed Unsuppression (H->Any)

    # Remove-from-Service (Any->I)

    # Return-to-Service (I->Any)

    return state
