"""
Alarm states and transition paths.

See ANSI/ISA 18.2 Management of Alarm Systems for the Process Industries
https://www.isa.org/store/ansi/isa-182-2016/46962105

"""


# FIXME - probably need to automatically ACK RTN_UNACK alerts based on timeout
from flask import current_app

from alerta.models.alarms.base import AlarmModel
from alerta.models.enums import Action, State
from alerta.models.severity import ALL_OK, NOT_OK, Severity

ACTIVE = [
    State.UNACK,
    State.ACK,
    State.RTN_UNACK,
    State.LATCHED_UNACK,
    State.LATCHED_ACK
]
INACTIVE = [
    State.NORMAL,
    State.SHELVED,
    State.SUPPRESSED_BY_DESIGN,
    State.OUT_OF_SERVICE
]


class Lifecycle(AlarmModel):

    def transition(self, previous_severity, current_severity, previous_status=None, current_status=None, **kwargs):
        state = previous_status or State.NORMAL
        action = kwargs.get('action', None)
        latched = kwargs.get('is_latched', False)

        # Alarm Occurs, Normal (A) -> Unack (B)
        if state == State.NORMAL:
            if current_severity in NOT_OK:
                return current_severity, State.UNACK
        # Operator Ack, Unack (B) -> Ack (C)
        if state == State.UNACK:
            if action == Action.ACTION_ACK:
                return current_severity, State.ACK
        # Re-Alarm, Ack (C) -> Unack (B)
        if state == State.ACK:
            if Severity.trend(previous_severity, current_severity) == Severity.MORE_SEVERE:
                return current_severity, State.UNACK
        # Process RTN Alarm Clears, Ack (C) -> Normal (A)
        if state == State.ACK and not latched:
            if current_severity in ALL_OK:
                return current_severity, State.NORMAL
        # Process RTN Latched Alarm, Ack (C) -> Latch Ack (F)
        if state == State.ACK and latched:
            if current_severity in ALL_OK:
                return current_severity, State.LATCHED_ACK
        # Process RTN and Alarm Clears, Unack (B) -> RTN Unack (D)
        if state == State.UNACK and not latched:
            if current_severity in ALL_OK:
                return current_severity, State.RTN_UNACK
        # Process RTN, Unack (B) -> Latch Unack (E)
        if state == State.UNACK and latched:
            if current_severity in ALL_OK:
                return current_severity, State.LATCHED_UNACK
        # Operator Ack, RTN Unack (D) -> Normal (A)
        if state == State.RTN_UNACK:
            if action == Action.ACTION_ACK:
                return current_severity, State.NORMAL
        # Re-Alarm Unack, RTN Unack (D) -> Unack (B)  # XXX - missing from descriptions?
        if state == State.RTN_UNACK:
            if current_severity in NOT_OK:
                return current_severity, State.UNACK
        # Operator Resets, Latch Unack (E) -> RTN Unack (D)
        if state == State.LATCHED_UNACK:
            if action == Action.ACTION_RESET:
                return current_severity, State.RTN_UNACK
        # Operator Ack, Latch Unack (E) -> Latch Ack (F)
        if state == State.LATCHED_UNACK:
            if action == Action.ACTION_ACK:
                return current_severity, State.LATCHED_ACK
        # Operator Resets, Latch Ack (F) -> Normal (A)
        if state == State.LATCHED_ACK:
            if action == Action.ACTION_RESET:
                return current_severity, State.NORMAL
        # Shelve (Any->G)
        if action == Action.ACTION_SHELVE:
            return current_severity, State.SHELVED
        # Unshelve (G->Any)
        if action == Action.ACTION_UNSHELVE:
            return current_severity, State.UNACK
        # Designed Suppression (Any->H)

        # Designed Unsuppression (H->Any)

        # Remove-from-Service (Any->I)

        # Return-to-Service (I->Any)

        return current_severity, state

    def get_config(self):

        filters = [
            {
                'name': 'All',
                'value': [s.value for s in list(State)]
            },
            {
                'name': 'Active',
                'value': [s.value for s in ACTIVE]
            },
            {
                'name': 'Shelved',
                'value': [State.SHELVED.value]
            },
            {
                'name': 'Out-of-Service',
                'value': [State.OUT_OF_SERVICE.value]
            },
            {
                'name': 'Inactive',
                'value': [s.value for s in INACTIVE]
            }
        ]

        return {
            'type': current_app.config['ALARM_MODEL'],
            'filters': filters
        }

    def is_suppressed(self, status):
        return status in [State.SUPPRESSED_BY_DESIGN, State.OUT_OF_SERVICE]
