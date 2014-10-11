
import abc
import pkg_resources


class PluginBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def pre_receive(self, alert):
        """Reject an alert based on alert properties."""
        return

    @abc.abstractmethod
    def post_receive(self, alert):
        """Send an alert to another service or notify users."""
        return


def load_backend(namespace='alerta.backends', name=None):

    for ep in pkg_resources.iter_entry_points(group=namespace, name=name):
        if ep:
            try:
                backend = ep.load()
            except Exception:
                return
            return backend


class BaseBackend(object):

    def get_severity(self, alert):

        raise NotImplementedError

    def get_status(self, alert):

        raise NotImplementedError

    def get_count(self, query=None):

        raise NotImplementedError

    def get_alerts(self, query=None, fields=None, sort=None, limit=0):

        raise NotImplementedError

    def get_history(self, query=None, fields=None, limit=0):

        raise NotImplementedError

    def is_duplicate(self, alert):

        raise NotImplementedError

    def is_correlated(self, alert):

        raise NotImplementedError

    def save_duplicate(self, alert):

        raise NotImplementedError

    def save_correlated(self, alert):

        raise NotImplementedError

    def create_alert(self, alert):

        raise NotImplementedError

    def get_alert(self, id):

        raise NotImplementedError

    def set_status(self, id, status, text=None):

        raise NotImplementedError

    def tag_alert(self, id, tags):

        raise NotImplementedError

    def untag_alert(self, id, tags):

        raise NotImplementedError

    def delete_alert(self, id):

        raise NotImplementedError

    def get_counts(self, query=None, fields=None, group=None):

        raise NotImplementedError

    def get_topn(self, query=None, group=None, limit=10):

        raise NotImplementedError

    def get_environments(self, query=None, fields=None, limit=0):

        raise NotImplementedError

    def get_services(self, query=None, fields=None, limit=0):

        raise NotImplementedError

    def get_heartbeats(self):

        raise NotImplementedError

    def save_heartbeat(self, heartbeat):

        raise NotImplementedError

    def get_heartbeat(self, id):

        raise NotImplementedError

    def delete_heartbeat(self, id):

        raise NotImplementedError

    def get_users(self):

        raise NotImplementedError

    def is_user_valid(self, user):

        raise NotImplementedError

    def save_user(self, args):

        raise NotImplementedError

    def delete_user(self, user):

        raise NotImplementedError

    def get_metrics(self):

        raise NotImplementedError

    def get_keys(self, query=None):

        raise NotImplementedError

    def is_key_valid(self, key):

        raise NotImplementedError

    def create_key(self, args):

        raise NotImplementedError

    def update_key(self, key):

        raise NotImplementedError

    def delete_key(self, key):

        raise NotImplementedError

    def is_token_valid(self, token):

        raise NotImplementedError

    def save_token(self, token):

        raise NotImplementedError

    def disconnect(self):

        raise NotImplementedError
