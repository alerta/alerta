
import abc
import logging
import pkg_resources

from alerta import settings

LOG = logging.getLogger(__name__)


class PluginBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def send(self, alert):
        """Send alert to downstream system."""
        return


def load_plugins(namespace='alerta.plugins'):

    plugins = []
    for ep in list(pkg_resources.iter_entry_points(namespace)):
        LOG.debug('Found plugin %r', ep)
        try:
            plugin = ep.load()
            if plugin:
                if ep.name in settings.PLUGINS:
                    plugins.append(plugin())
                else:
                    LOG.info("%s plugin not enabled", ep.name)
        except Exception as e:
            LOG.error('Could not load %r: %s', ep.name, e)
    return plugins