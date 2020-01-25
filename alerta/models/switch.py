from typing import List  # noqa


class SwitchState:
    ON = True
    OFF = False

    @staticmethod
    def to_state(string):
        return SwitchState.ON if string == 'ON' else SwitchState.OFF

    @staticmethod
    def to_string(state):
        return 'ON' if state else 'OFF'


class Switch:

    switches = []  # type: List[Switch]

    def __init__(self, name, title=None, description=None, state=SwitchState.ON):

        self.group = 'switch'
        self.name = name
        self.title = title
        self.description = description
        self.state = state

        Switch.switches.append(self)

    def serialize(self):
        return {
            'group': 'switch',
            'name': self.name,
            'type': 'text',
            'title': self.title,
            'description': self.description,
            'value': 'ON' if self.is_on else 'OFF',
        }

    def __repr__(self):
        return 'Switch(name={!r}, description={!r}, state={!r})'.format(
            self.name, self.description, SwitchState.to_string(self.state)
        )

    @classmethod
    def find_by_name(cls, name):
        for s in Switch.switches:
            if s.name == name:
                return s
        return

    @classmethod
    def find_all(cls):
        return Switch.switches

    def set_state(self, state):
        self.state = SwitchState.to_state(state)

    @property
    def is_on(self):
        return self.state
