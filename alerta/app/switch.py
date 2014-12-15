

class SwitchState(object):
    ON = True
    OFF = False

    @staticmethod
    def to_state(string):
        return SwitchState.ON if string == "ON" else SwitchState.OFF

    @staticmethod
    def to_string(state):
        return "ON" if state else "OFF"


class Switch(object):

    switches = []

    def __init__(self, name, description=None, state=SwitchState.ON):

        self.name = name
        self.description = description
        self.state = state

        Switch.switches.append(self)

    def __repr__(self):
        return 'Switch(name=%s, description=%s, state=%s)' % (self.name, self.description,
                                                              SwitchState.to_string(self.state))

    @classmethod
    def get(cls, name):
        for s in Switch.switches:
            if s.name == name:
                return s
        return None

    @classmethod
    def get_all(cls):
        return Switch.switches

    def set_state(self, state):
        self.state = SwitchState.to_state(state)

    def is_on(self):
        return self.state
