from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from alerta.app import db
from alerta.database.base import Query
from alerta.utils.response import absolute_url

JSON = Dict[str, Any]


class Customer:

    def __init__(self, match: str, customer: str, **kwargs) -> None:

        self.id = kwargs.get('id', str(uuid4()))
        self.match = match
        self.customer = customer

    @classmethod
    def parse(cls, json: JSON) -> 'Customer':
        return Customer(
            match=json.get('match', None),
            customer=json.get('customer', None)
        )

    @property
    def serialize(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'href': absolute_url('/customer/' + self.id),
            'match': self.match,
            'customer': self.customer
        }

    def __repr__(self) -> str:
        return 'Customer(id={!r}, match={!r}, customer={!r})'.format(
            self.id, self.match, self.customer)

    @classmethod
    def from_document(cls, doc: Dict[str, Any]) -> 'Customer':
        return Customer(
            id=doc.get('id', None) or doc.get('_id'),
            match=doc.get('match', None),
            customer=doc.get('customer', None)
        )

    @classmethod
    def from_record(cls, rec) -> 'Customer':
        return Customer(
            id=rec.id,
            match=rec.match,
            customer=rec.customer
        )

    @classmethod
    def from_db(cls, r: Union[Dict, Tuple]) -> 'Customer':
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)

    def create(self) -> 'Customer':
        return Customer.from_db(db.create_customer(self))

    @staticmethod
    def find_by_id(id: str) -> Optional['Customer']:
        return Customer.from_db(db.get_customer(id))

    @staticmethod
    def find_all(query: Query=None) -> List['Customer']:
        return [Customer.from_db(customer) for customer in db.get_customers(query)]

    def delete(self) -> bool:
        return db.delete_customer(self.id)

    @classmethod
    def lookup(cls, login: str, groups: List[str]) -> List[str]:
        customers = db.get_customers_by_match(login, matches=groups)
        return customers if customers != '*' else []
