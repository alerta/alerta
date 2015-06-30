import json
import datetime
import requests

from flask import request, render_template
from flask.ext.cors import cross_origin

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from alerta.app import app
from alerta.alert import Alert
from alerta.app.utils import jsonify, jsonp
from alerta.app.metrics import Timer

LOG = app.logger

oembed_timer = Timer('oEmbed', 'request', 'oEmbed request', 'Total time to process number of oEmbed requests')

@app.route('/oembed', defaults={'format': 'json'})
@app.route('/oembed.<format>', methods=['OPTIONS', 'GET'])
@cross_origin()
@jsonp
def oembed(format):

    oembed_started = oembed_timer.start_timer()

    if format != 'json':
        oembed_timer.stop_timer(oembed_started)
        return jsonify(status="error", message="unsupported format: %s" % format), 400

    if 'url' not in request.args or 'maxwidth' not in request.args \
            or 'maxheight' not in request.args:
        oembed_timer.stop_timer(oembed_started)
        return jsonify(status="error", message="missing default parameters: url, maxwidth, maxheight"), 400

    try:
        url = request.args['url']
        key = request.args.get('api-key')
        width = int(request.args['maxwidth'])
        height = int(request.args['maxheight'])
        title = request.args.get('title', 'Alerts')
    except Exception as e:
        oembed_timer.stop_timer(oembed_started)
        return jsonify(status="error", message=str(e)), 400

    try:
        o = urlparse(url)
    except Exception as e:
        oembed_timer.stop_timer(oembed_started)
        return jsonify(status="error", message=str(e)), 500

    headers = dict()
    if key:
        headers = {'Authorization': 'Key ' + key}
    response = requests.get(url=url, headers=headers)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        oembed_timer.stop_timer(oembed_started)
        return jsonify(status="error", message=str(e)), response.status_code

    if o.path.endswith('/alerts/count'):

        counts = response.json().get('severityCounts', dict())

        max = 'normal'
        if counts.get('warning', 0) > 0:
            max = 'warning'
        if counts.get('minor', 0) > 0:
            max = 'minor'
        if counts.get('major', 0) > 0:
            max = 'major'
        if counts.get('critical', 0) > 0:
            max = 'critical'

        html = render_template(
            'oembed/counts.html',
            title=title,
            width=width,
            height=height,
            max=max,
            counts=counts
        )
        oembed_timer.stop_timer(oembed_started)
        return jsonify(version="1.0", type="rich", width=width, height=height, title=title,  provider_name="Alerta", provider_url=request.url_root, html=html)

    else:
        oembed_timer.stop_timer(oembed_started)
        return jsonify(status="error", message="unsupported oEmbed URL scheme"), 400


@app.route('/embed.js', methods=['OPTIONS', 'GET'])
def embed_js():

    return app.send_static_file('embed.js')
