
import os
import sys
import re
import fnmatch
import yaml

from alerta.common import config
from alerta.common import log as logging

CONF = config.CONF
LOG = logging.getLogger(__name__)

prog = os.path.basename(sys.argv[0])


class Transformers(object):

    transform_opts = {
        'yaml_config': '/etc/alerta/%s.yaml' % prog,
        'parser_dir': '/etc/alerta/parsers',
    }

    @staticmethod
    def normalise_alert(alert, trapoid=None, facility=None, level=None, **kwargs):
        """
        Transforms alert based on configuration contained in YAML file.
        """

        config.register_opts(Transformers.transform_opts)

        if not CONF.yaml_config:
            return

        LOG.info('Transform alert %s using %s', alert.id, CONF.yaml_config)

        if not os.path.exists(CONF.yaml_config):
            return

        suppress = False

        try:
            conf = yaml.load(open(CONF.yaml_config))
            LOG.info('Loaded %d transformer configurations OK', len(conf))
        except Exception, e:
            LOG.error('Failed to load transformer configuration %s: %s', CONF.yaml_config, e)
            raise RuntimeError

        for c in conf:
            LOG.debug('YAML config: %s', c)

            match = None
            pattern = None

            if alert.event_type == 'snmptrapAlert' and trapoid and c.get('trapoid'):
                match = re.match(c['trapoid'], trapoid)
                pattern = trapoid
            elif alert.event_type == 'syslogAlert' and facility and level and c.get('priority'):
                match = fnmatch.fnmatch('%s.%s' % (facility, level), c['priority'])
                pattern = c['priority']
            elif c.get('match'):
                try:
                    match = all(item in alert.__dict__.items() for item in c['match'].items())
                    pattern = c['match'].items()
                except AttributeError:
                    pass

            if match:
                LOG.debug('Matched %s for %s', pattern, alert.event_type)

                # 1. Simple substitutions
                if 'resource' in c:
                    alert.resource = c['resource']
                if 'event' in c:
                    alert.event = c['event']
                if 'environment' in c:
                    alert.environment = c['environment']
                if 'severity' in c:
                    alert.severity = c['severity']
                if 'correlate' in c:
                    alert.correlate = c['correlate']
                if 'status' in c:
                    alert.correlate = c['status']
                if 'service' in c:
                    alert.service = c['service']
                if 'group' in c:
                    alert.group = c['group']
                if 'value' in c:
                    alert.value = c['value']
                if 'text' in c:
                    alert.text = c['text']
                if 'tags' in c:
                    alert.tags.append(c['tags'])  # join tags
                if 'attributes' in c:
                    alert.attributes.update(c['attributes'])  # merge attributes
                if 'origin' in c:
                    alert.timeout = c['origin']
                if 'event_type' in c:
                    alert.timeout = c['event_type']
                if 'timeout' in c:
                    alert.timeout = c['timeout']

                # 2. Complex transformations
                if 'parser' in c:
                    LOG.debug('Loading parser %s', c['parser'])

                    context = kwargs
                    context.update(alert.__dict__)

                    try:
                        exec(open('%s/%s.py' % (CONF.parser_dir, c['parser']))) in globals(), context
                        LOG.info('Parser %s/%s exec OK', CONF.parser_dir, c['parser'])
                    except Exception, e:
                        LOG.warning('Parser %s failed: %s', c['parser'], e)
                        raise RuntimeError

                    for k, v in context.iteritems():
                        if hasattr(alert, k):
                            setattr(alert, k, v)

                    if 'suppress' in context:
                        suppress = context['suppress']

                # 3. Suppress based on results of 1 or 2
                if 'suppress' in c:
                    suppress = suppress or c['suppress']

        return suppress
