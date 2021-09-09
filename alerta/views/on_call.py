from flask import current_app, g, jsonify, request
from flask_cors import cross_origin

from alerta.app import qb
from alerta.auth.decorators import permission
from alerta.exceptions import ApiError
from alerta.models.on_call import OnCall
from alerta.models.enums import Scope
from alerta.utils.api import assign_customer
from alerta.utils.audit import write_audit_trail
from alerta.utils.paging import Page
from alerta.utils.response import absolute_url, jsonp
from alerta.models.alert import Alert

from . import api


@api.route("/oncalls", methods=["OPTIONS", "POST"])
@cross_origin()
@permission(Scope.write_on_calls)
@jsonp
def create_on_call():
    try:
        on_call = OnCall.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    if Scope.admin in g.scopes or Scope.admin_on_calls in g.scopes:
        on_call.user = on_call.user or g.login
    else:
        on_call.user = g.login

    on_call.customer = assign_customer(wanted=on_call.customer, permission=Scope.admin_on_calls)

    try:
        on_call = on_call.create()
    except Exception as e:
        raise ApiError(str(e), 500)

    write_audit_trail.send(
        current_app._get_current_object(),
        event="on_call-created",
        message="",
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=on_call.id,
        type="on_call",
        request=request,
    )

    if on_call:
        return (
            jsonify(status="ok", id=on_call.id, onCall=on_call.serialize),
            201,
            {"Location": absolute_url("/oncall/" + on_call.id)},
        )
    else:
        raise ApiError("insert oncall failed", 500)


@api.route("/oncalls/<on_call_id>", methods=["OPTIONS", "GET"])
@cross_origin()
@permission(Scope.read_on_calls)
@jsonp
def get_on_call(on_call_id):
    on_call = OnCall.find_by_id(on_call_id)

    if on_call:
        return jsonify(status="ok", total=1, onCall=on_call.serialize)
    else:
        raise ApiError("not found", 404)


@api.route("/oncalls/active", methods=["OPTIONS", "POST"])
@cross_origin()
@permission(Scope.read_on_calls)
@jsonp
def get_on_calls_active():
    try:
        alert = Alert.parse(request.json)
    except Exception as e:
        raise ApiError(str(e), 400)

    on_calls = [oncall.serialize for oncall in OnCall.find_all_active(alert)]
    total = len(on_calls)
    return jsonify(status="ok", total=total, onCalls=on_calls)


@api.route("/oncalls", methods=["OPTIONS", "GET"])
@cross_origin()
@permission(Scope.read_on_calls)
@jsonp
def list_on_calls():
    query = qb.on_calls.from_params(request.args, customers=g.customers)
    total = OnCall.count(query)
    paging = Page.from_params(request.args, total)
    on_calls = OnCall.find_all(query, page=paging.page, page_size=paging.page_size)

    if on_calls:
        return jsonify(
            status="ok",
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            onCalls=[on_call.serialize for on_call in on_calls],
            total=total,
        )
    else:
        return jsonify(
            status="ok",
            page=paging.page,
            pageSize=paging.page_size,
            pages=paging.pages,
            more=paging.has_more,
            message="not found",
            onCalls=[],
            total=0,
        )


@api.route("/oncalls/<on_call_id>", methods=["OPTIONS", "PUT"])
@cross_origin()
@permission(Scope.write_on_calls)
@jsonp
def update_on_call(on_call_id):
    if not request.json:
        raise ApiError("nothing to change", 400)

    if not current_app.config["AUTH_REQUIRED"]:
        on_call = OnCall.find_by_id(on_call_id)
    elif Scope.admin in g.scopes or Scope.admin_on_calls in g.scopes:
        on_call = OnCall.find_by_id(on_call_id)
    else:
        on_call = OnCall.find_by_id(on_call_id, g.customers)

    if not on_call:
        raise ApiError("not found", 404)

    update = request.json
    update["user"] = g.login
    update["customer"] = assign_customer(wanted=update.get("customer"), permission=Scope.admin_on_calls)

    write_audit_trail.send(
        current_app._get_current_object(),
        event="on_call-updated",
        message="",
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=on_call.id,
        type="on_call",
        request=request,
    )

    updated = on_call.update(**update)
    if updated:
        return jsonify(status="ok", onCall=updated.serialize)
    else:
        raise ApiError("failed to update oncall", 500)


@api.route("/oncalls/<on_call_id>", methods=["OPTIONS", "DELETE"])
@cross_origin()
@permission(Scope.write_on_calls)
@jsonp
def delete_on_call(on_call_id):
    customer = g.get("customer", None)
    on_call = OnCall.find_by_id(on_call_id, customer)

    if not on_call:
        raise ApiError("not found", 404)

    write_audit_trail.send(
        current_app._get_current_object(),
        event="on_call-deleted",
        message="",
        user=g.login,
        customers=g.customers,
        scopes=g.scopes,
        resource_id=on_call.id,
        type="on_call",
        request=request,
    )

    if on_call.delete():
        return jsonify(status="ok")
    else:
        raise ApiError("failed to delete oncall", 500)
