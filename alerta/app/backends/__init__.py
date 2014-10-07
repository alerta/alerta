
class Backend(object):

    def create_indexes(self):

        raise NotImplemented

    def get_severity(self, alert):

        raise NotImplemented

    def get_status(self, alert):

        raise NotImplemented

    def get_count(self, query=None):

        raise NotImplemented

    def get_alerts(self, query=None, fields=None, sort=None, limit=0):

        raise NotImplemented

    def get_history(self, query=None, fields=None, limit=0):

        raise NotImplemented

    def is_duplicate(self, alert):

        raise NotImplemented

    def is_correlated(self, alert):

        raise NotImplemented

    def save_duplicate(self, alert):

        raise NotImplemented

    def save_correlated(self, alert):

        raise NotImplemented

    def create_alert(self, alert):

        raise NotImplemented

    def get_alert(self, id):

        raise NotImplemented

    def set_status(self, id, status, text=None):

        raise NotImplemented

    def tag_alert(self, id, tags):

        raise NotImplemented

    def untag_alert(self, id, tags):

        raise NotImplemented

    def delete_alert(self, id):

        raise NotImplemented

    def get_counts(self, query=None):

        raise NotImplemented

    def get_topn(self, query=None, group=None, limit=10):

        raise NotImplemented

    def get_environments(self, query=None, fields=None, limit=0):

        raise NotImplemented

    def get_services(self, query=None, fields=None, limit=0):

        raise NotImplemented

    def get_heartbeats(self):

        raise NotImplemented

    def save_heartbeat(self, heartbeat):

        raise NotImplemented

    def get_heartbeat(self, id):

        raise NotImplemented

    def delete_heartbeat(self, id):

        raise NotImplemented

    def get_users(self):

        raise NotImplemented

    def is_user_valid(self, user):

        raise NotImplemented

    def save_user(self, args):

        raise NotImplemented

    def delete_user(self, user):

        raise NotImplemented

    def get_metrics(self):

        raise NotImplemented

    def get_keys(self, query=None):

        raise NotImplemented

    def is_key_valid(self, key):

        raise NotImplemented

    def create_key(self, args):

        raise NotImplemented

    def update_key(self, key):

        raise NotImplemented

    def delete_key(self, key):

        raise NotImplemented

    def is_token_valid(self, token):

        raise NotImplemented

    def save_token(self, token):

        raise NotImplemented

    def disconnect(self):

        raise NotImplemented
