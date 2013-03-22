m = re.search('(?P<module>\S+) (?P<thread>\S+) (?P<level>DEBUG|INFO|AUDIT|WARNING|ERROR|CRITICAL|TRACE) - (?P<text>.*)', text)
if m:
    resource = resource + ':' +  m.group('module')
    value = m.group('level')
    text = m.group('text')
    tags.append('thread:%s' % m.group('thread'))
else:
    LOG.warning('No match: locals = %s', locals())

# clean-up temp variables
del m
