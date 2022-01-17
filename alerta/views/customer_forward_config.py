from flask import request
from flask_cors import cross_origin

from alerta.utils.response import jsonp
from . import api


@api.route('/forward-config', methods=['OPTIONS', 'POST'])
@cross_origin()
@jsonp
def forward_config_setup():
    request_paylaod = request.get_json(silent=True)
    print("Customer forward config is ", request_paylaod)
    pass
