from types import Union
from typing import Dict, Tuple

from alerta.app import db
from alerta.models.alert import Alert


class EventLog:
    def __init__(self, event_name, resource, customer_id, event_properties, environment, id=None):
        self.id = id
        self.event_name = event_name
        self.resource = resource
        self.customer_id = customer_id
        self.event_properties = event_properties
        self.environment = environment

    def create(self):
        return EventLog.from_db(db.create_event_log(self))

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'EventLog':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    @classmethod
    def from_record(cls, rec) -> 'EventLog':
        return EventLog(rec.event_name, rec.resource, rec.customer_id, rec.event_properties, rec.environment, rec.id)

    @classmethod
    def from_document(cls):
        raise NotImplementedError()

    @staticmethod
    def from_alert(alert: Alert):
        return EventLog(alert.event, alert.resource, alert.customer, alert.serialize, alert.environment)

    @staticmethod
    def multiplex_event_log(event_log):
        return db.multiplex_event_log(event_log)
