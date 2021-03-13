from urllib.parse import parse_qs, urlparse

from flask import current_app, jsonify, render_template, request
from flask_cors import cross_origin

from alerta.app import db, qb
from alerta.auth.decorators import permission
from alerta.models.enums import Scope
from alerta.utils.response import jsonp

from . import api


@api.route('/oembed', defaults={'format': 'json'}, methods=['OPTIONS', 'GET'])
@api.route('/oembed.<format>', methods=['OPTIONS', 'GET'])
@cross_origin()
@permission(Scope.read_oembed)
@jsonp
def oembed(format):
    try:
        url = request.args['url']
        title = request.args['title']
    except Exception as e:
        return jsonify(status='error', message=str(e)), 400

    try:
        o = urlparse(url)
    except Exception as e:
        return jsonify(status='error', message=str(e)), 400

    if o.path.endswith('/alerts/count'):
        try:
            query = qb.alerts.from_params(parse_qs(o.query))
            severity_count = db.get_counts_by_severity(query)
        except Exception as e:
            return jsonify(status='error', message=str(e)), 500

        max = 'none'
        if severity_count.get('informational', 0) > 0:
            max = 'informational'
        if severity_count.get('warning', 0) > 0:
            max = 'warning'
        if severity_count.get('minor', 0) > 0:
            max = 'minor'
        if severity_count.get('major', 0) > 0:
            max = 'major'
        if severity_count.get('critical', 0) > 0:
            max = 'critical'

        html = render_template(
            'oembed/counts.html',
            title=title,
            max=max,
            counts=severity_count
        )
        headers = {
            'Access-Control-Allow-Origin': '*'
        }
        return jsonify(version='1.0', type='rich', title=title, provider_name='Alerta', provider_url=request.url_root, html=html), 200, headers

    elif o.path.endswith('/alerts/top10/count'):
        # TODO: support top10 oembed widget
        pass
    else:
        return jsonify(status='error', message='unsupported oEmbed URL scheme'), 400


@api.route('/embed.js', methods=['OPTIONS', 'GET'])
def embed_js():

    return current_app.send_static_file('embed.js')
