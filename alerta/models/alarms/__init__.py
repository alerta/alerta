from importlib import import_module


class Base:
    pass


def load_alarm_model(model):
    try:
        return import_module('alerta.models.alarms.%s' % model.lower())
    except Exception:
        raise ImportError('Failed to load %s alarm model' % model)


class AlarmModel(Base):

    Severity = {}  # type: ignore
    Colors = {}  # type: ignore

    DEFAULT_STATUS = None  # type: str
    DEFAULT_NORMAL_SEVERITY = None  # type: str
    DEFAULT_PREVIOUS_SEVERITY = None  # type: str
    NORMAL_SEVERITY_LEVEL = None  # type: str

    def __init__(self, app=None):
        self.app = None
        if app is not None:
            self.register(app)

    def init_app(self, app):
        cls = load_alarm_model(app.config['ALARM_MODEL'])
        self.__class__ = type('AlarmModelImpl', (cls.StateMachine, AlarmModel), {})
        try:
            self.register(app)
        except Exception as e:
            app.logger.warning(e)

    def register(self, app):
        raise NotImplementedError

    def trend(self, previous, current):
        raise NotImplementedError

    def transition(self, alert, current_status=None, previous_status=None, action=None, **kwargs):
        raise NotImplementedError

    @staticmethod
    def is_suppressed(alert):
        raise NotImplementedError
