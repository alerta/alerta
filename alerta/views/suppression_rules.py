import logging

from flask import request, jsonify
from flask_cors import cross_origin

from alerta.auth.decorators import permission
from alerta.models.enums import Scope
from alerta.utils.response import jsonp

from . import api
from ..exceptions import ApiError
from ..models.SuppressionRule import SuppressionRule
from ..models.channel import DeveloperChannel

log_object = logging.getLogger('alerta.views.suppression_rules')


@api.route("/suppression-rule", methods=['POST'])
@cross_origin()
@permission(Scope.write_rules)
@jsonp
def create_suppression_rule():
    try:
        suppression_rule = SuppressionRule.parse(request.json)
        suppression_rule = suppression_rule.create()
    except Exception as e:
        return jsonify(status='error', message=str(e)), 400
    if not suppression_rule:
        raise ApiError("Cannot create developer channel")
    return jsonify(status='ok', channel=suppression_rule.serialize)
