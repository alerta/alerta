from enum import Enum


class Severity(str, Enum):

    Security = 'security'
    Critical = 'critical'
    Major = 'major'
    Minor = 'minor'
    Warning = 'warning'
    Indeterminate = 'indeterminate'
    Informational = 'informational'
    Normal = 'normal'
    Ok = 'ok'
    Cleared = 'cleared'
    Debug = 'debug'
    Trace = 'trace'
    Unknown = 'unknown'


class Status(str, Enum):

    Open = 'open'
    Assign = 'assign'
    Ack = 'ack'
    Shelved = 'shelved'
    Blackout = 'blackout'
    Closed = 'closed'
    Expired = 'expired'
    Unknown = 'unknown'
    Not_Valid = 'notValid'


class Action(str, Enum):

    OPEN = 'open'
    ASSIGN = 'assign'
    ACK = 'ack'
    UNACK = 'unack'
    SHELVE = 'shelve'
    UNSHELVE = 'unshelve'
    CLOSE = 'close'
    EXPIRED = 'expired'
    TIMEOUT = 'timeout'


class TrendIndication(str, Enum):

    More_Severe = 'moreSevere'
    No_Change = 'noChange'
    Less_Severe = 'lessSevere'


class Scope(str, Enum):

    read = 'read'
    write = 'write'
    admin = 'admin'
    read_alerts = 'read:alerts'
    write_alerts = 'write:alerts'
    delete_alerts = 'delete:alerts'
    admin_alerts = 'admin:alerts'
    read_blackouts = 'read:blackouts'
    write_blackouts = 'write:blackouts'
    admin_blackouts = 'admin:blackouts'
    read_twilio_rules = 'read:twilio_rules'
    write_twilio_rules = 'write:twilio_rules'
    admin_twilio_rules = 'admin:twilio_rules'
    read_heartbeats = 'read:heartbeats'
    write_heartbeats = 'write:heartbeats'
    admin_heartbeats = 'admin:heartbeats'
    write_users = 'write:users'
    admin_users = 'admin:users'
    read_groups = 'read:groups'
    admin_groups = 'admin:groups'
    read_perms = 'read:perms'
    admin_perms = 'admin:perms'
    read_customers = 'read:customers'
    admin_customers = 'admin:customers'
    read_keys = 'read:keys'
    write_keys = 'write:keys'
    admin_keys = 'admin:keys'
    write_webhooks = 'write:webhooks'
    read_oembed = 'read:oembed'
    read_management = 'read:management'
    admin_management = 'admin:management'
    read_userinfo = 'read:userinfo'

    @property
    def action(self):
        return self.split(':')[0]

    @property
    def resource(self):
        try:
            return self.split(':')[1]
        except IndexError:
            return None

    @staticmethod
    def from_str(action: str, resource: str = None):
        """Return a scope based on the supplied action and resource.

        :param action: the scope action eg. read, write, delete or admin
        :param resource: the specific resource of the scope, if any eg. alerts,
            blackouts, heartbeats, users, perms, customers, keys, webhooks,
            oembed, management or userinfo or None
        :return: Scope
        """
        if resource:
            return Scope('{}:{}'.format(action, resource))
        else:
            return Scope(action)


ADMIN_SCOPES = [Scope.admin, Scope.read, Scope.write]


class ChangeType(str, Enum):

    open = 'open'
    assign = 'assign'
    ack = 'ack'
    unack = 'unack'
    shelve = 'shelve'
    unshelve = 'unshelve'
    close = 'close'

    new = 'new'
    action = 'action'
    status = 'status'
    value = 'value'
    severity = 'severity'
    note = 'note'
    timeout = 'timeout'
    expired = 'expired'


class NoteType(str, Enum):

    alert = 'alert'
    blackout = 'blackout'
    customer = 'customer'
    group = 'group'
    heartbeat = 'heartbeat'
    key = 'api-key'
    perm = 'permission'
    user = 'user'
