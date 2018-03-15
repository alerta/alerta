import logging
from collections import OrderedDict

from pkg_resources import iter_entry_points, load_entry_point, DistributionNotFound

from alerta.plugins import app

LOG = logging.getLogger('alerta.plugins')


class Plugins(object):

    def __init__(self):
        self.plugins = OrderedDict()
        self.rules = None

        app.init_app()  # fake app for plugin config

    def register(self, app):

        entry_points = {}
        for ep in iter_entry_points('alerta.plugins'):
            LOG.debug("Server plugin '%s' installed.", ep.name)
            entry_points[ep.name] = ep

        for name in app.config['PLUGINS']:
            try:
                plugin = entry_points[name].load()
                if plugin:
                    self.plugins[name] = plugin()
                    LOG.info("Server plugin '%s' enabled.", name)
            except Exception as e:
                LOG.error("Server plugin '%s' could not be loaded: %s", name, e)
        LOG.info("All server plugins enabled: %s", ', '.join(self.plugins.keys()))
        try:
            self.rules = load_entry_point('alerta-routing', 'alerta.routing', 'rules')
        except (DistributionNotFound, ImportError):
            LOG.info('No plugin routing rules found. All plugins will be evaluated.')

    def routing(self, alert):
        try:
            if self.plugins and self.rules:
                return self.rules(alert, self.plugins)
        except Exception as e:
            LOG.warning("Plugin routing rules failed: %s", str(e))

        return self.plugins.values()
