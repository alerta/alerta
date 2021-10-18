from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple, Union, TYPE_CHECKING
from uuid import uuid4

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.response import absolute_url
from alerta.models.notification_channel import NotificationChannel

if TYPE_CHECKING:
    from alerta.models.alert import Alert

JSON = Dict[str, Any]


class AdvancedSeverity:
    def __init__(self, _from: 'list[str]', _to: 'list[str]') -> None:
        self.from_ = _from
        self.to = _to

    @property
    def serialize(self):
        return {
            'from': self.from_,
            'to': self.to
        }

    def __repr__(self):
        return 'AdvancedSeverity(from={!r}, to={!r})'.format(
            self.from_, self.to)

    @classmethod
    def from_document(cls, doc):
        return AdvancedSeverity(
            _from=doc.get('from', list()),
            _to=doc.get('to', list())
        )

    @classmethod
    def from_record(cls, rec):
        return AdvancedSeverity(
            _from=rec.from_,
            _to=rec.to,
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)


class NotificationRule:
    def __init__(
        self, environment: str, channel_id: str, receivers: List[str], use_oncall: bool, **kwargs
    ) -> None:
        if not environment:
            raise ValueError('Missing mandatory value for "environment"')
        if not channel_id:
            raise ValueError('Missing mandatory value for "notification_channel"')
        if not type(receivers) == list:
            raise ValueError('Missing mandatory value for "receivers"')

        self.id = kwargs.get("id") or str(uuid4())
        self.environment = environment
        self.channel_id = channel_id
        self.receivers = receivers
        self.use_oncall = use_oncall
        self.start_time: time = kwargs.get("start_time") or None
        self.end_time: time = kwargs.get("end_time") or None
        self.severity = kwargs.get("severity") or list()
        self.service = kwargs.get("service", None) or list()
        self.resource = kwargs.get("resource", None)
        self.event = kwargs.get("event", None)
        self.group = kwargs.get("group", None)
        self.tags = kwargs.get("tags", None) or list()
        self.customer = kwargs.get("customer", None)
        self.days = kwargs.get("days", None) or list()
        self.advanced_severity = kwargs.get("advanced_severity") or [AdvancedSeverity([], [])]
        self.use_advanced_severity = kwargs.get("use_advanced_severity", False)

        self.user = kwargs.get("user", None)
        self.create_time = (
            kwargs["create_time"] if "create_time" in kwargs else datetime.utcnow()
        )
        self.text = kwargs.get("text", None)

        if self.environment:
            self.priority = 1
        if self.resource and not self.event:
            self.priority = 2
        elif self.service:
            self.priority = 3
        elif self.event and not self.resource:
            self.priority = 4
        elif self.group:
            self.priority = 5
        elif self.resource and self.event:
            self.priority = 6
        elif self.tags:
            self.priority = 7

    @property
    def channel(self):
        return NotificationChannel.find_by_id(self.channel_id)

    @classmethod
    def parse(cls, json: JSON) -> "NotificationRule":
        if not isinstance(json.get("service", []), list):
            raise ValueError("service must be a list")
        if not isinstance(json.get("tags", []), list):
            raise ValueError("tags must be a list")
        notification_rule = NotificationRule(
            id=json.get("id", None),
            environment=json["environment"],
            channel_id=json["channelId"],
            receivers=json["receivers"],
            use_oncall=json.get("useOnCall", False),
            severity=json.get("severity", list()),
            advanced_severity=[AdvancedSeverity(severity["from"], severity["to"]) for severity in json.get("advancedSeverity", [])],
            use_advanced_severity=json.get("useAdvancedSeverity", False),
            service=json.get("service", list()),
            resource=json.get("resource", None),
            event=json.get("event", None),
            group=json.get("group", None),
            tags=json.get("tags", list()),
            customer=json.get("customer", None),
            start_time=(
                datetime.strptime(json["startTime"], "%H:%M").time()
                if json["startTime"] is not None and json["startTime"] != ""
                else None
            )
            if "startTime" in json
            else None,
            end_time=(
                datetime.strptime(json["endTime"], "%H:%M").time()
                if json["endTime"] is not None and json["endTime"] != ""
                else None
            )
            if "endTime" in json
            else None,
            user=json.get("user", None),
            text=json.get("text", None),
            days=json.get("days", None),
        )
        return notification_rule

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "href": absolute_url("/notificationrule/" + self.id),
            "priority": self.priority,
            "environment": self.environment,
            "channelId": self.channel_id,
            "receivers": self.receivers,
            "useOnCall": self.use_oncall,
            "service": self.service,
            "severity": self.severity,
            "advancedSeverity": [a_severity.serialize for a_severity in self.advanced_severity],
            "useAdvancedSeverity": self.use_advanced_severity,
            "resource": self.resource,
            "event": self.event,
            "group": self.group,
            "tags": self.tags,
            "customer": self.customer,
            "user": self.user,
            "createTime": self.create_time,
            "text": self.text,
            "startTime": self.start_time.strftime("%H:%M")
            if self.start_time is not None
            else None,
            "endTime": self.end_time.strftime("%H:%M")
            if self.end_time is not None
            else None,
            "days": self.days,
        }

    def __repr__(self) -> str:
        more = ""
        if self.service:
            more += "service=%r, " % self.service
        if self.resource:
            more += "resource=%r, " % self.resource
        if self.event:
            more += "event=%r, " % self.event
        if self.group:
            more += "group=%r, " % self.group
        if self.tags:
            more += "tags=%r, " % self.tags
        if self.customer:
            more += "customer=%r, " % self.customer
        if self.severity:
            more += "severity=%r, " % self.severity
        if self.advanced_severity:
            more += "advanced_severity=%r, " % self.advanced_severity
        if self.use_advanced_severity:
            more += "use_advanced_severity=%r, " % self.use_advanced_severity

        return "NotificationRule(id={!r}, priority={!r}, environment={!r}, receivers={!r}, {})".format(
            self.id,
            self.priority,
            self.environment,
            self.receivers,
            more,
        )

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> "NotificationRule":
        return NotificationRule(
            id=doc.get("id", None) or doc.get("_id"),
            priority=doc.get("priority", None),
            environment=doc["environment"],
            channel_id=doc["channelId"],
            receivers=doc.get("receivers") or list(),
            use_oncall=doc.get("useOnCall", False),
            service=doc.get("service", list()),
            severity=doc.get("severity", list()),
            advanced_severity=[AdvancedSeverity.from_db(advanced_severity) for advanced_severity in doc.get("advancedSeverity", [])],
            use_advanced_severity=doc.get("useAdvancedSeverity", list()),
            resource=doc.get("resource", None),
            event=doc.get("event", None),
            group=doc.get("group", None),
            tags=doc.get("tags", list()),
            customer=doc.get("customer", None),
            user=doc.get("user", None),
            create_time=doc.get("createTime", None),
            text=doc.get("text", None),
            start_time=(
                datetime.strptime(
                    f'{doc["startTime"] :.2f}'.replace(".", ":"), "%H:%M"
                ).time()
                if doc["startTime"] is not None
                else None
            )
            if "startTime" in doc
            else None,
            end_time=(
                datetime.strptime(
                    f'{doc["endTime"] :.2f}'.replace(".", ":"), "%H:%M"
                ).time()
                if doc["endTime"] is not None
                else None
            )
            if "endTime" in doc
            else None,
            days=doc.get("days", None),
        )

    @classmethod
    def from_record(cls, rec) -> "NotificationRule":
        return NotificationRule(
            id=rec.id,
            priority=rec.priority,
            environment=rec.environment,
            channel_id=rec.channel_id,
            receivers=rec.receivers,
            use_oncall=rec.use_oncall,
            service=rec.service,
            severity=rec.severity,
            advanced_severity=[AdvancedSeverity.from_db(advanced_severity) for advanced_severity in rec.advanced_severity or []],
            use_advanced_severity=rec.use_advanced_severity,
            resource=rec.resource,
            event=rec.event,
            group=rec.group,
            tags=rec.tags,
            customer=rec.customer,
            user=rec.user,
            create_time=rec.create_time,
            text=rec.text,
            start_time=rec.start_time,
            end_time=rec.end_time,
            days=rec.days,
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> "NotificationRule":
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    # create a notification rule
    def create(self) -> "NotificationRule":
        # self.advanced_severity = [AdvancedSeverity(_from=advanced_severity["from"], _to=advanced_severity["to"]) for advanced_severity in self.advanced_severity]
        return NotificationRule.from_db(db.create_notification_rule(self))

    # get a notification rule
    @staticmethod
    def find_by_id(
        id: str, customers: List[str] = None
    ) -> Optional["NotificationRule"]:
        return NotificationRule.from_db(db.get_notification_rule(id, customers))

    @staticmethod
    def find_all(
        query: Query = None, page: int = 1, page_size: int = 1000
    ) -> List["NotificationRule"]:
        return [
            NotificationRule.from_db(notification_rule)
            for notification_rule in db.get_notification_rules(query, page, page_size)
        ]

    @staticmethod
    def count(query: Query = None) -> int:
        return db.get_notification_rules_count(query)

    @ staticmethod
    def find_all_active(alert: "Alert") -> "list[NotificationRule]":
        if alert.duplicate_count:
            return []
        return [NotificationRule.from_db(db_notification_rule) for db_notification_rule in db.get_notification_rules_active(alert)]

    def update(self, **kwargs) -> "NotificationRule":
        return NotificationRule.from_db(db.update_notification_rule(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_notification_rule(self.id)
