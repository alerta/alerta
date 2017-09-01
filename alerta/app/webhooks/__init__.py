
from flask import Blueprint, request

from alerta.app.exceptions import ApiError

webhooks = Blueprint('webhooks', __name__)

from . import cloudwatch, grafana, newrelic, pagerduty, pingdom, prometheus, riemann, serverdensity, stackdriver, telegram


@webhooks.before_request
def only_json():
    if request.method in ['POST', 'PUT'] and not request.is_json:
        raise ApiError("POST and PUT requests must set 'Content-type' to 'application/json'", 415)
