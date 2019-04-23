import logging
from collections import OrderedDict
from typing import TYPE_CHECKING

from flask import Config, Flask
from pkg_resources import (DistributionNotFound, iter_entry_points,
                           load_entry_point)

from alerta.plugins import app

LOG = logging.getLogger('alerta.plugins')

if TYPE_CHECKING:
    from typing import Iterable, Tuple  # noqa
    from alerta.models.alert import Alert  # noqa
    from alerta.plugins import PluginBase  # noqa


class Plugins:

    def __init__(self) -> None:
        self.plugins = OrderedDict()  # type: OrderedDict[str, PluginBase]
        self.rules = None  # entry point

        self.config = Config('/')

        app.init_app()  # fake app for plugin config (deprecated)

    def register(self, app: Flask) -> None:
        self.config = app.config

        entry_points = {}
        for ep in iter_entry_points('alerta.plugins'):
            LOG.debug("Server plugin '{}' found.".format(ep.name))
            entry_points[ep.name] = ep

        for name in self.config['PLUGINS']:
            try:
                plugin = entry_points[name].load()
                if plugin:
                    self.plugins[name] = plugin()
                    LOG.info("Server plugin '{}' loaded.".format(name))
            except Exception as e:
                LOG.error("Failed to load plugin '{}': {}".format(name, str(e)))
        LOG.info('All server plugins enabled: {}'.format(', '.join(self.plugins.keys())))
        try:
            self.rules = load_entry_point('alerta-routing', 'alerta.routing', 'rules')  # type: ignore
        except (DistributionNotFound, ImportError):
            LOG.info('No plugin routing rules found. All plugins will be evaluated.')

    def routing(self, alert: 'Alert') -> 'Tuple[Iterable[PluginBase], Config]':
        try:
            if self.plugins and self.rules:
                try:
                    r = self.rules(alert, self.plugins, config=self.config)
                except TypeError:
                    r = self.rules(alert, self.plugins)

                if isinstance(r, list):
                    return r, self.config
                else:
                    plugins, config = r
                    return plugins, Config('/', {**self.config, **config})

        except Exception as e:
            LOG.warning('Plugin routing rules failed: {}'.format(e))

        # default when no routing rules defined
        return self.plugins.values(), self.config
