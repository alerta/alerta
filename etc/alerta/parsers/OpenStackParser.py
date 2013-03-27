m = re.search('(?P<level>DEBUG|INFO|AUDIT|WARNING|ERROR|CRITICAL|TRACE) \[?(?P<module>[^] ]+)\]?( \[(?P<uuid>[^]]+)\])? (?P<text>.*)', text)
if m:
    resource = resource + ':' + m.group('module')
    value = m.group('level')
    text = m.group('text')
    uuid = m.group('uuid').partition(' ')[0] if m.group('uuid') else 'none'
    tags.append('uuid:%s' % uuid)
else:
    LOG.warning('No match: locals = %s', locals())

if 'Checking Token' in text:
    suppress = True

# clean-up temp variables
del m
