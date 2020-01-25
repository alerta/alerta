from flask import Blueprint

mgmt = Blueprint('mgmt', __name__)

from . import views  # noqa isort:skip
