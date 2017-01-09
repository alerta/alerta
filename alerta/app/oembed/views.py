from alerta.app import app, db
from alerta.app.auth import auth_required
from alerta.app.utils import jsonp, parse_fields
from alerta.app.metrics import Timer

from flask import request, render_template, jsonify
from flask_cors import cross_origin
from werkzeug import urls
from werkzeug.datastructures import ImmutableMultiDict

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


LOG = app.logger

oembed_timer = Timer('oEmbed', 'request', 'oEmbed request', 'Total time to process number of oEmbed requests')

@app.route('/oembed', defaults={'format':'json'}, methods=['OPTIONS', 'GET'])
@app.route('/oembed.<format>', methods=['OPTIONS', 'GET'])
@cross_origin()
@auth_required
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
        width = int(request.args['maxwidth'])
        height = int(request.args['maxheight'])
        title = request.args.get('title', 'Alerts')
    except Exception as e:
        oembed_timer.stop_timer(oembed_started)
        return jsonify(status="error", message=str(e)), 400

    try:
        o = urlparse(url)
        params = ImmutableMultiDict(urls.url_decode(o.query))
        query, _, _, _, _, _, _ = parse_fields(params)
    except Exception as e:
        oembed_timer.stop_timer(oembed_started)
        return jsonify(status="error", message=str(e)), 500

    if o.path.endswith('/alerts/count'):
        try:
            severity_count = db.get_counts(query=query, fields={"severity": 1}, group="severity")
        except Exception as e:
            return jsonify(status="error", message=str(e)), 500

        max = 'normal'
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
            width=width,
            height=height,
            max=max,
            counts=severity_count
        )
        oembed_timer.stop_timer(oembed_started)
        return jsonify(version="1.0", type="rich", width=width, height=height, title=title,  provider_name="Alerta", provider_url=request.url_root, html=html)

    elif o.path.endswith('/alerts/top10/count'):
        # TODO: support top10 oembed widget
        pass
    else:
        oembed_timer.stop_timer(oembed_started)
        return jsonify(status="error", message="unsupported oEmbed URL scheme"), 400


@app.route('/embed.js', methods=['OPTIONS', 'GET'])
def embed_js():

    return app.send_static_file('embed.js')
