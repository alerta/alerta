
from uuid import uuid4

from alerta.app import db
from alerta.utils.api import absolute_url


class Customer(object):

    def __init__(self, match, customer, **kwargs):

        self.id = kwargs.get('id', str(uuid4()))
        self.match = match
        self.customer = customer

    @classmethod
    def parse(cls, json):
        return Customer(
            match=json.get('match', None),
            customer=json.get('customer', None)
        )

    @property
    def serialize(self):
        return {
            'id': self.id,
            'href': absolute_url('/customer/' + self.id),
            'match': self.match,
            'customer': self.customer
        }

    def __repr__(self):
        return 'Customer(id=%r, match=%r, customer=%r)' % (
            self.id, self.match, self.customer)

    @classmethod
    def from_document(cls, doc):
        return Customer(
            id=doc.get('id', None) or doc.get('_id'),
            match=doc.get('match', None),
            customer=doc.get('customer', None)
        )

    @classmethod
    def from_record(cls, rec):
        return Customer(
            id=rec.id,
            match=rec.match,
            customer=rec.customer
        )

    @classmethod
    def from_db(cls, r):
        if isinstance(r, dict):
            return cls.from_document(r)
        elif isinstance(r, tuple):
            return cls.from_record(r)
        else:
            return

    def create(self):
        return Customer.from_db(db.create_customer(self))

    @staticmethod
    def get(id):
        return Customer.from_db(db.get_customer(id))

    @staticmethod
    def find_all(query=None):
        return [Customer.from_db(customer) for customer in db.get_customers(query)]

    def delete(self):
        return db.delete_customer(self.id)

    @classmethod
    def lookup(cls, login, groups):
        customer = db.get_customers_by_match(login, matches=groups)
        return customer if customer != '*' else None
