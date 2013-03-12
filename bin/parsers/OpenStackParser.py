# LOG.debug('locals = %s', locals())

m = re.search('[DEBUG|INFO|WARNING|CRITICAL|TRACE] (?P<event>\S+) \[.*\] (?P<text>.*)', text)
if m:
    msg = m.groupdict()
    event = msg['event']
    text = msg['text']
    value = msg['sev']
else:
    tags.append('no match')

if 'Checking Token' in text:
    suppress = True
