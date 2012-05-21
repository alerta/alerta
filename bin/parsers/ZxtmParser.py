
# Set severity
if trapvars['$3'].startswith('SERIOUS'):
    severity = 'MAJOR'
elif trapvars['$3'].startswith('WARN'):
    severity = 'WARNING'
    
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
