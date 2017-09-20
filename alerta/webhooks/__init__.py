
from flask import Blueprint

webhooks = Blueprint('webhooks', __name__)

from . import cloudwatch, grafana, newrelic, pagerduty, pingdom, prometheus, riemann
from . import serverdensity, slack, stackdriver, telegram
