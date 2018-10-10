
from flask import jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.customer import Customer
from alerta.utils.response import jsonp

from . import api


@api.route('/customer', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission('admin:customers')
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

    if customer:
        return jsonify(status='ok', id=customer.id, customer=customer.serialize), 201
    else:
        raise ApiError('create customer lookup failed', 500)


@api.route('/customers', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:customers')
@jsonp
def list_customers():
    query = qb.from_params(request.args)
    customers = Customer.find_all(query)

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


@api.route('/customer/<customer_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission('admin:customers')
@jsonp
def delete_customer(customer_id):
    customer = Customer.find_by_id(customer_id)

    if not customer:
        raise ApiError('not found', 404)

    if customer.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete customer', 500)
