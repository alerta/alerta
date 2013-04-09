#
# OracleLogParser.py
#
# @return string severity
#   MAJOR, WARNING, NORMAL
# @return string environment
#   REL, QA, TEST, CODE, STAGE, DEV, LWP
# @return string severity
#   MAJOR ( timeout=4days ), MINOR, WARNING
# @return string group
#   Database
# @return string event
#   ORA-00600, ORA-00060, etc
# @return string value
#   ERROR
# @return string enviroment
#   PROD or DEV
# @return string service
#   R2
# @return string more_info:
#   "http://www.oracle.com/pls/db10g/error_search?search=%" % ora
# @return string threshold
#   na
# @return string correlate
#   na
# @return string graphs
#   na
# @append string tag
#   oracle and oracle/<SID>
# @text "Apr  3 12:51:01 codoradb01 oracle/CONTENT: ORA-279 signalled during: ALTER DATABASE RECOVER    CONTINUE DEFAULT  ..."
m = re.search('(?P<env>rel|qa|tst|cod|stg|dev|lwp)ora\S+ (?P<sid>oracle\/\S+): (?P<text>ORA-(?P<error>\d+).*)', rawData)

# Set severity
errors = {
    'ORA-00060': 'major',
    'ORA-00279': '-',
    'ORA-00283': '-',
    'ORA-00308': 'minor',
    'ORA-00444': 'minor',
    'ORA-00448': 'minor',
    'ORA-00600': 'major',
    'ORA-00942': 'minor',
    'ORA-00959': 'minor',
    'ORA-01031': 'minor',
    'ORA-01089': 'minor',
    'ORA-01092': 'major',
    'ORA-01109': 'minor',
    'ORA-01110': '-',
    'ORA-01122': 'major',
    'ORA-01124': 'minor',
    'ORA-01153': '-',
    'ORA-01157': 'minor',
    'ORA-01186': 'major',
    'ORA-01195': 'minor',
    'ORA-01203': 'minor',
    'ORA-01507': 'minor',
    'ORA-01547': 'minor',
    'ORA-01578': 'major',
    'ORA-03135': 'minor',
    'ORA-04045': 'minor',
    'ORA-04063': 'minor',
    'ORA-06508': 'minor',
    'ORA-06512': '-',
    'ORA-06550': 'minor',
    'ORA-07445': 'major',
    'ORA-10456': 'minor',
    'ORA-12012': 'minor',
    'ORA-12514': 'minor',
    'ORA-16037': '-',
    'ORA-16145': '-',
    'ORA-19815': 'major',
    'ORA-26040': 'major',
    'ORA-27037': 'major',
    'ORA-38706': 'minor',
    'ORA-38713': 'minor',
}

# Set environment
env = {
    # '': 'PROD',
    'rel': 'REL',
    'qa' : 'QA',
    'tst': 'TEST',
    'cod': 'CODE',
    'stg': 'STAGE',
    'dev': 'DEV',
    'lwp': 'LWP'
}
   
if m:
    event = "ORA-%05d" % int(m.group('error'))
    group = 'Database'
    value = 'ERROR'
    environment = [ env[m.group('env')] ]
    service = [ 'R2' ]
    text = m.group('text')
    tags.append(m.group('sid'))
    moreInfo = "http://www.oracle.com/pls/db10g/error_search?search=%s" % event

else:
    LOG.warning('No match: locals = %s', locals())

if event in errors:
    severity = errors[event]
    if errors[event] == 'major':
        timeout = 345600
    elif errors[event] == '-':
        suppress = True

else:
    severity = 'major'
    LOG.warning('Unknown %s error',  event, locals())

# clean-up temp variables
del m
del env
del errors
