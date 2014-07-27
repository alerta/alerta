
import abc
import pkg_resources

from alerta.app import app

LOG = app.logger


class PluginBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def send(self, alert):
        """Send alert to downstream system."""
        return


def load_plugins(namespace='alerta.plugins'):

    plugins = []
    for ep in list(pkg_resources.iter_entry_points(namespace)):
        LOG.debug('Found plug-in %r', ep)
        try:
            if ep.name in app.config['PLUGINS']:
                plugin = ep.load()
                if plugin:
                    plugins.append(plugin())
            else:
                LOG.info("%s plug-in not enabled", ep.name)
        except Exception as e:
            LOG.error('Could not load plug-in %s: %s', ep.name, e)
    return plugins