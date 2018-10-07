
class AlarmModel:

    def trend(self, previous, current):
        raise NotImplementedError

    def transition(self, previous_severity, current_severity, previous_status=None, current_status=None, action=None):
        raise NotImplementedError

    @staticmethod
    def is_suppressed(alert):
        raise NotImplementedError
