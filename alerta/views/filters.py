from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.enums import Scope
from alerta.models.filter import Filter
from alerta.utils.api import assign_customer
from alerta.utils.audit import write_audit_trail
from alerta.utils.paging import Page
from alerta.utils.response import absolute_url, jsonp

from . import api


@api.route('/filter', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.write_filters)
@jsonp
def create_filter():
    try:
        filter = Filter.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    if Scope.admin in g.scopes or Scope.admin_filters in g.scopes:
        filter.user = filter.user or g.login
    else:
        filter.user = g.login

    filter.customer = assign_customer(wanted=filter.customer, permission=Scope.admin_filters)

    try:
        filter = filter.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(current_app._get_current_object(), event='filter-created', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=filter.id, type='filter', request=request)

    if filter:
        return jsonify(status='ok', id=filter.id, filter=filter.serialize), 201, {'Location': absolute_url('/filter/' + filter.id)}
    else:
        raise ApiError('insert filter failed', 500)


@api.route('/filter/<filter_id>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_filters)
@jsonp
def get_filter(filter_id):
    filter = Filter.find_by_id(filter_id)

    if filter:
        return jsonify(status='ok', total=1, filter=filter.serialize)
    else:
        raise ApiError('not found', 404)


@api.route('/filters', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_filters)
@jsonp
def search_filters():
    query = qb.filters.from_params(request.args, customers=g.customers)
    total = Filter.count(query)
    paging = Page.from_params(request.args, total)
    filters = Filter.find_all(query, page=paging.page, page_size=paging.page_size)

    if filters:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            filters=[filter.serialize for filter in filters],
            total=total
        )
    else:
        return jsonify(
            status='ok',
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            message='not found',
            filters=[],
            total=0
        )


@api.route('/filter/<filter_id>', methods=['OPTIONS', 'PUT'])
@cross_origin()
@permission(Scope.write_filters)
@jsonp
def update_filter(filter_id):
    if not request.json:
        raise ApiError('nothing to change', 400)

    if not current_app.config['AUTH_REQUIRED']:
        filter = Filter.find_by_id(filter_id)
    elif Scope.admin in g.scopes or Scope.admin_filters in g.scopes:
        filter = Filter.find_by_id(filter_id)
    else:
        filter = Filter.find_by_id(filter_id, g.customers)

    if not filter:
        raise ApiError('not found', 404)

    try:
        Filter.validate_inputs(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    update = request.json
    update['user'] = g.login
    update['customer'] = assign_customer(wanted=update.get('customer'), permission=Scope.admin_filters)

    write_audit_trail.send(current_app._get_current_object(), event='filter-updated', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=filter.id, type='filter',
                           request=request)

    updated = filter.update(**update)
    if updated:
        return jsonify(status='ok', filter=updated.serialize)
    else:
        raise ApiError('failed to update filter', 500)


@api.route('/filter/<filter_id>', methods=['OPTIONS', 'DELETE'])
@cross_origin()
@permission(Scope.write_filters)
@jsonp
def delete_filter(filter_id):
    customer = g.get('customer', None)
    filter = Filter.find_by_id(filter_id, customer)

    if not filter:
        raise ApiError('not found', 404)

    write_audit_trail.send(current_app._get_current_object(), event='filter-deleted', message='', user=g.login,
                           customers=g.customers, scopes=g.scopes, resource_id=filter.id, type='filter', request=request)

    if filter.delete():
        return jsonify(status='ok')
    else:
        raise ApiError('failed to delete filter', 500)
