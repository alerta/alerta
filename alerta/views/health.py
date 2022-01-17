import logging

from flask import jsonify
from flask_cors import cross_origin

from . import api
from ..models.healthcheck import HealthCheck

log_object = logging.getLogger('alerta.views.health')


@api.route("/health", methods=['GET'])
@cross_origin()
def health_endpoint():
    try:
        return jsonify(status='ok', message={"status": "up", **HealthCheck.health_check()}), 200
    except Exception as e:
        return jsonify(status='error', message=dict(status="down", error=e)), 400
