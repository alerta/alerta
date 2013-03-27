#
# ZxtmTrapParser.py
#
# @param dict trapvars
#   $3 is the SNMP trap text
#
# @return string severity
#   MAJOR, WARNING, NORMAL
# @return string environment
#   REL, QA, TEST, CODE, STAGE, DEV, LWP

# Set severity
if trapvars['$3'].startswith('SERIOUS'):
    severity = 'MAJOR'
elif trapvars['$3'].startswith('WARN'):
    severity = 'WARNING'
else:
    severity = 'NORMAL'
    
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
m = re.search('(\W|gu)(?P<env>rel|qa|tst|cod|stg|dev|lwp)', trapvars['$3'])
if m:
    environment = env[m.group('env')]
