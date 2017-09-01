
from alerta.app import config


class App(object):

    def __init__(self):
        self.config = config.get_user_config()

app = App()  # fake app for config only
