
from flask import jsonify, request, g
from flask_cors import cross_origin

from alerta.app.auth.utils import permission
from alerta.app.models.customer import Customer
from alerta.app.utils.api import jsonp
from alerta.app.exceptions import ApiError

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
        return jsonify(status="ok", id=customer.id, customer=customer.serialize), 201
    else:
        raise ApiError("create customer lookup failed", 500)


@api.route('/customers', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission('read:customers')
@jsonp
def list_customers():
    customers = Customer.find_all()

    if customers:
        return jsonify(
            status="ok",
            customers=[customer.serialize for customer in customers],
            total=len(customers)
        )
    else:
        return jsonify(
            status="ok",
            message="not found",
            customers=[],
            total=0
        )


@api.route('/customer/<customer_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission('admin:customers')
@jsonp
def delete_customer(customer_id):
    customer = Customer.get(customer_id)

    if not customer:
        raise ApiError("not found", 404)

    if customer.delete():
        return jsonify(status="ok")
    else:
        raise ApiError("failed to delete customer", 500)
