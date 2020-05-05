from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.customer import Customer
from alerta.models.enums import Scope
from alerta.utils.audit import admin_audit_trail
from alerta.utils.response import jsonp

from . import api


@api.route('/customer', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.admin_customers)
@jsonp
def create_customer():
    try:
        customer = Customer.parse(request.json)
    except ValueError as e:
        raise ApiError(str(e), 400)

    try:
        customer = customer.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    admin_audit_trail.send(current_app._get_current_object(), event='customer-created', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=customer.id, type='customer', request=request)

    if customer:
        return jsonify(status='ok', id=customer.id, customer=customer.serialize), 201
    else:
        raise ApiError('create customer lookup failed', 500)


@api.route('/customer/<customer_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_customers)
@jsonp
def get_customer(customer_id):
    customer = Customer.find_by_id(customer_id)

    if Scope.admin in g.scopes or Scope.admin_customers in g.scopes or customer.customer in g.customers:
        return jsonify(status='ok', total=1, customer=customer.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/customers', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_customers)
@jsonp
def list_customers():
    query = qb.from_params(request.args, customers=g.customers)
    customers = [
        c for c in Customer.find_all(query)
        if Scope.admin in g.scopes or Scope.admin_customers in g.scopes or c.customer in g.customers
    ]

    if customers:
        return jsonify(
            status='ok',
            customers=[customer.serialize for customer in customers],
            total=len(customers)
        )
    else:
        return jsonify(
            status='ok',
            message='not found',
            customers=[],
            total=0
        )


@api.route('/customer/<customer_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.admin_customers)
@jsonp
def update_customer(customer_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    customer = Customer.find_by_id(customer_id)

    if not customer:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='customer-updated', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=customer.id, type='customer', request=request)

    updated = customer.update(**request.json)
    if updated:
        return jsonify(status='ok', customer=updated.serialize)
    else:
        raise ApiError('failed to update customer', 500)


@api.route('/customer/<customer_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.admin_customers)
@jsonp
def delete_customer(customer_id):
    customer = Customer.find_by_id(customer_id)

    if not customer:
        raise ApiError('not found', 404)

    admin_audit_trail.send(current_app._get_current_object(), event='customer-deleted', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=customer.id, type='customer', request=request)

    if customer.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete customer', 500)
