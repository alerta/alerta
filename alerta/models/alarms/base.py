from importlib import import_module


class Base:
    pass


def get_alarm_model(app):
    return app.config['ALARM_MODEL'].lower()


def load_alarm_model(model):
    try:
        return import_module('alerta.models.alarms.{}'.format(model))
    except Exception:
        raise ImportError('Failed to load {} alarm model'.format(model))


class AlarmModel(Base):

    def __init__(self, app=None):
        self.app = None
        if app is not None:
            self.register(app)

    def register(self, app):
        model = get_alarm_model(app)
        cls = load_alarm_model(model)
        self.__class__ = type('AlarmModelImpl', (cls.Lifecycle, AlarmModel), {})

    def transition(self, previous_severity, current_severity, previous_status=None, current_status=None, **kwargs):
        raise NotImplementedError
