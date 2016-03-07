
import abc
import pkg_resources

from six import add_metaclass
from alerta.app import app

LOG = app.logger


class RejectException(Exception):
    """The alert was rejected because the format did not meet the required policy."""


@add_metaclass(abc.ABCMeta)
class PluginBase(object):
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


def load_plugins(namespace='alerta.plugins'):

    plugins = []
    for ep in list(pkg_resources.iter_entry_points(namespace)):
        LOG.debug("Server plug-in '%s' found.", ep.name)
        try:
            if ep.name in app.config['PLUGINS']:
                plugin = ep.load()
                if plugin:
                    plugins.append(plugin())
                    LOG.info("Server plug-in '%s' enabled.", ep.name)
            else:
                LOG.debug("Server plug-in '%s' not enabled in 'PLUGINS'.", ep.name)
        except Exception as e:
            LOG.error("Server plug-in '%s' could not be loaded: %s", ep.name, e)
    return plugins
