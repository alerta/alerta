import logging
from collections import OrderedDict

from pkg_resources import iter_entry_points

from alerta.plugins import app

LOG = logging.getLogger('alerta.actions')


class Actions(object):

    def __init__(self):
        self.actions = OrderedDict()
        self.rules = None

        app.init_app()  # fake app for action config

    def register(self, app):

        entry_points = {}
        for ep in iter_entry_points('alerta.actions'):
            LOG.debug("Server action '%s' installed.", ep.name)
            entry_points[ep.name] = ep

        for name in app.config['ACTIONS']:
            try:
                action = entry_points[name].load()
                if action:
                    self.actions[name] = action()
                    LOG.info("Server action '%s' enabled.", name)
            except Exception as e:
                LOG.error("Server action '%s' could not be loaded: %s", name, e)
        LOG.info("All server actions enabled: %s", ', '.join(self.actions.keys()))
