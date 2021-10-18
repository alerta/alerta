import uuid

from flask import jsonify, request
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.models.enums import Scope
from alerta.utils.response import jsonp
from . import api
from ..models.Rules import Rule


@api.route('/rule', methods=['OPTIONS', 'POST'])
@cross_origin()
@permission(Scope.admin_customers)
@jsonp
def create_customer_alert_forward_rule():
    request_payload = request.get_json(silent=True)
    rule = Rule(id=uuid.uuid4().hex, **request_payload)
    try:
        rule = rule.create()
    except Exception as e:
        return jsonify(status='error', message=str(e)), 400
    return jsonify(status='ok', id=rule.id, rule=rule.serialize), 201
