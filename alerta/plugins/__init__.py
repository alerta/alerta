
import abc
import logging
from collections import OrderedDict

from pkg_resources import iter_entry_points, load_entry_point, DistributionNotFound
from six import add_metaclass


LOG = logging.getLogger('alerta.plugins')


@add_metaclass(abc.ABCMeta)
class PluginBase(object):

    def __init__(self, name=None):
        self.name = name or self.__module__

    @abc.abstractmethod
    def pre_receive(self, alert):
        """Pre-process an alert based on alert properties or reject it by raising RejectException."""
        return alert

    @abc.abstractmethod
    def post_receive(self, alert):
        """Send an alert to another service or notify users."""
        return None

    @abc.abstractmethod
    def status_change(self, alert, status, text):
        """Trigger integrations based on status changes."""
        return None


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


class FakeApp(object):

    def init_app(self):
        from alerta.app import config
        self.config = config.get_user_config()

app = FakeApp()  # used for plugin config only
