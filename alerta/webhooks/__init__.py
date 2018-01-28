
from flask import Blueprint, request, current_app

webhooks = Blueprint('webhooks', __name__)

from . import cloudwatch, grafana, graylog, newrelic, pagerduty, pingdom, prometheus, riemann
from . import serverdensity, slack, stackdriver, telegram


@webhooks.before_request
def before_request():
    current_app.logger.info('Webhook Request:\n{} {}\n\n{}{}'.format(
        request.method,
        request.url,
        request.headers,
        request.get_data().decode('utf-8')
    ))
