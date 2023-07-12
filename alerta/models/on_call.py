from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from alerta.app import db
from alerta.database.base import Query
from alerta.models.user import User
from alerta.utils.response import absolute_url

if TYPE_CHECKING:
    from alerta.models.alert import Alert

JSON = Dict[str, Any]


class OnCall:
    def __init__(self, **kwargs) -> None:

        self.id = kwargs.get('id') or str(uuid4())
        self.user_ids = kwargs.get('user_ids') or []
        self.group_ids = kwargs.get('group_ids') or []
        self.start_date = kwargs.get('start_date')
        self.end_date = kwargs.get('end_date')
        self.start_time = kwargs.get('start_time')
        self.end_time = kwargs.get('end_time')
        self.repeat_type = kwargs.get('repeat_type')
        self.repeat_days = kwargs.get('repeat_days')
        self.repeat_weeks = kwargs.get('repeat_weeks')
        self.repeat_months = kwargs.get('repeat_months')

        self.customer = kwargs.get('customer')
        self.user = kwargs.get('user')

        self.create_time = kwargs['create_time'] if 'create_time' in kwargs else datetime.utcnow()

    @property
    def users(self):
        group_users = [db.get_group_users(group_id) for group_id in self.group_ids]
        users = {User.find_by_id(user_id) for user_id in self.user_ids}
        for user_list in group_users:
            for user in user_list:
                users.add(User.find_by_id(user.id))
        return users

    @ classmethod
    def parse(cls, json: JSON) -> 'OnCall':
        user_ids = json.get('userIds', [])
        group_ids = json.get('groupIds', [])
        if not isinstance(user_ids, list):
            raise ValueError('userIds must be a list')
        if not isinstance(group_ids, list):
            raise ValueError('groupIds must be a list')
        if len(user_ids) == 0 and len(group_ids) == 0:
            raise ValueError('missing userIds to alert')

        on_call = OnCall(
            id=json.get('id'),
            user_ids=json.get('userIds'),
            group_ids=json.get('groupIds'),
            start_date=json.get('startDate'),
            end_date=json.get('endDate'),
            start_time=(
                datetime.strptime(json['startTime'], '%H:%M').time()
                if json['startTime'] is not None and json['startTime'] != ''
                else None
            )
            if 'startTime' in json
            else None,
            end_time=(
                datetime.strptime(json['endTime'], '%H:%M').time()
                if json['endTime'] is not None and json['endTime'] != ''
                else None
            )
            if 'endTime' in json
            else None,
            repeat_type=json.get('repeatType'),
            repeat_days=json.get('repeatDays'),
            repeat_weeks=json.get('repeatWeeks'),
            repeat_months=json.get('repeatMonths'),
            customer=json.get('customer'),
            user=json.get('user'),
        )
        return on_call

    @ property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/oncalls/' + self.id),
            'userIds': self.user_ids,
            'groupIds': self.group_ids,
            'startDate': self.start_date,
            'endDate': self.end_date,
            'startTime': self.start_time.strftime('%H:%M') if self.start_time is not None else None,
            'endTime': self.end_time.strftime('%H:%M') if self.end_time is not None else None,
            'repeatType': self.repeat_type,
            'repeatDays': self.repeat_days,
            'repeatWeeks': self.repeat_weeks,
            'repeatMonths': self.repeat_months,
            'customer': self.customer,
            'user': self.user,
        }

    def __repr__(self) -> str:
        more = ''
        if self.user_ids:
            more += 'user_ids=%r, ' % self.user_ids
        if self.group_ids:
            more += 'group_ids=%r, ' % self.group_ids
        if self.customer:
            more += 'customer=%r, ' % self.customer

        return 'OnCall(id={!r}, {})'.format(
            self.id,
            more,
        )

    @ classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'OnCall':
        return OnCall(
            id=doc.get('id', None) or doc.get('_id'),
            user_ids=doc.get('userIds'),
            group_ids=doc.get('groupIds'),
            start_date=doc['startDate'].date().isoformat() if doc.get('startDate') is not None else None,
            end_date=doc['endDate'].date().isoformat() if doc.get('endDate') is not None else None,
            start_time=(
                datetime.strptime(f'{doc["startTime"] :.2f}'.replace('.', ':'), '%H:%M').time()
                if doc['startTime'] is not None
                else None
            )
            if 'startTime' in doc
            else None,
            end_time=(
                datetime.strptime(f'{doc["endTime"] :.2f}'.replace('.', ':'), '%H:%M').time()
                if doc['endTime'] is not None
                else None
            )
            if 'endTime' in doc
            else None,
            days=doc.get('days', None),
            repeat_type=doc.get('repeatType'),
            repeat_days=doc.get('repeatDays'),
            repeat_weeks=doc.get('repeatWeeks'),
            repeat_months=doc.get('repeatMonths'),
            # repeat_every_x_day=doc.get("repeatEveryXDay"),
            # repeat_every_x_week=doc.get("repeatEveryXWeek"),
            # repeat_every_x_month=doc.get("repeatEveryXMonth"),
            customer=doc.get('customer'),
            user=doc.get('user'),
        )

    @ classmethod
    def from_record(cls, rec) -> 'OnCall':
        return OnCall(
            id=rec.id,
            user_ids=rec.user_ids,
            group_ids=rec.group_ids,
            start_date=rec.start_date.strftime('%Y-%m-%d') if rec.start_date is not None else rec.start_date,
            end_date=rec.end_date.strftime('%Y-%m-%d') if rec.end_date is not None else rec.end_date,
            start_time=rec.start_time,
            end_time=rec.end_time,
            repeat_type=rec.repeat_type,
            repeat_days=rec.repeat_days,
            repeat_weeks=rec.repeat_weeks,
            repeat_months=rec.repeat_months,
            # repeat_every_x_day=rec.repeat_every_x_day,
            # repeat_every_x_week=rec.repeat_every_x_week,
            # repeat_every_x_month=rec.repeat_every_x_month,
            customer=rec.customer,
            user=rec.user,
        )

    @ classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'OnCall':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    # create a notification rule
    def create(self) -> 'OnCall':
        return OnCall.from_db(db.create_on_call(self))

    # get a notification rule
    @ staticmethod
    def find_by_id(id: str, customers: List[str] = None) -> Optional['OnCall']:
        return OnCall.from_db(db.get_on_call(id, customers))

    @ staticmethod
    def find_all(query: Query = None, page: int = 1, page_size: int = 1000) -> List['OnCall']:
        return [OnCall.from_db(on_call) for on_call in db.get_on_calls(query, page, page_size)]

    @ staticmethod
    def count(query: Query = None) -> int:
        return db.get_on_calls_count(query)

    @ staticmethod
    def find_all_active(alert: 'Alert') -> 'list[OnCall]':
        return [OnCall.from_db(db_oncall) for db_oncall in db.get_on_calls_active(alert)]

    def update(self, **kwargs) -> 'OnCall':
        return OnCall.from_db(db.update_on_call(self.id, **kwargs))

    def delete(self) -> bool:
        return db.delete_on_call(self.id)
