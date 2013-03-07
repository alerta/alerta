def transform(alert):
    # Load alert transforms
    try:
        alertconf = yaml.load(open(CONF.yaml_config))
        LOG.info('Loaded %d alert transforms and blackout rules OK', len(alertconf))
    except Exception, e:
        alertconf = dict()
        LOG.warning('Failed to load alert transforms and blackout rules: %s', e)

    suppress = False
    for conf in alertconf:
        LOG.debug('alertconf: %s', conf)
        if all(item in alert.items() for item in conf['match'].items()):
            if 'parser' in conf:
                LOG.debug('Loading parser %s', conf['parser'])
                try:
                    exec (open('%s/%s.py' % (CONF.parser_dir, conf['parser']))) in globals(), locals()
                    LOG.info('Parser %s/%s exec OK', CONF.parser_dir, conf['parser'])
                except Exception, e:
                    LOG.warning('Parser %s failed: %s', conf['parser'], e)
            if 'event' in conf:
                event = conf['event']
            if 'resource' in conf:
                resource = conf['resource']
            if 'severity' in conf:
                severity = conf['severity']
            if 'group' in conf:
                group = conf['group']
            if 'value' in conf:
                value = conf['value']
            if 'text' in conf:
                text = conf['text']
            if 'environment' in conf:
                environment = [conf['environment']]
            if 'service' in conf:
                service = [conf['service']]
            if 'tags' in conf:
                tags = conf['tags']
            if 'correlatedEvents' in conf:
                correlate = conf['correlatedEvents']
            if 'thresholdInfo' in conf:
                threshold = conf['thresholdInfo']
            if 'suppress' in conf:
                suppress = conf['suppress']
            break

    if suppress:
        LOG.info('%s : Suppressing alert %s', alert['id'], alert['summary'])
        return
