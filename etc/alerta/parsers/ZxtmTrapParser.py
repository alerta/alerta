
for var in varbinds:
    if 'fullLogLine' in var:
        full_log_line = varbinds[var].strip('"').split('\t')

resource = '%s:%s' % (resource.split('.')[0], full_log_line[1])

event = event.split('::')[1].rstrip('.0')

ZXTM_CORRELATED_EVENTS = {
    # fault tolerance
    'machineok': ['machineok', 'machinetimeout', 'machinefail', 'machinerecovered'],
    'machinetimeout': ['machineok', 'machinetimeout', 'machinefail', 'machinerecovered'],
    'machinefail': ['machineok', 'machinetimeout', 'machinefail', 'machinerecovered'],
    'machinerecovered': ['machineok', 'machinetimeout', 'machinefail', 'machinerecovered'],

    # state
    'statebaddata': ['statebaddata', 'stateconnfail', 'stateok', 'statereadfail', 'statetimeout', 'stateunexpected', 'statewritefail'],
    'stateconnfail': ['statebaddata', 'stateconnfail', 'stateok', 'statereadfail', 'statetimeout', 'stateunexpected', 'statewritefail'],
    'stateok': ['statebaddata', 'stateconnfail', 'stateok', 'statereadfail', 'statetimeout', 'stateunexpected', 'statewritefail'],
    'statereadfail': ['statebaddata', 'stateconnfail', 'stateok', 'statereadfail', 'statetimeout', 'stateunexpected', 'statewritefail'],
    'statetimeout': ['statebaddata', 'stateconnfail', 'stateok', 'statereadfail', 'statetimeout', 'stateunexpected', 'statewritefail'],
    'stateunexpected': ['statebaddata', 'stateconnfail', 'stateok', 'statereadfail', 'statetimeout', 'stateunexpected', 'statewritefail'],
    'statewritefail': ['statebaddata', 'stateconnfail', 'stateok', 'statereadfail', 'statetimeout', 'stateunexpected', 'statewritefail'],

    # conf
    'confdel': ['confdel', 'confmod', 'confadd', 'confok', 'confreptimeout', 'confrepfailed'],
    'confmod': ['confdel', 'confmod', 'confadd', 'confok', 'confreptimeout', 'confrepfailed'],
    'confadd': ['confdel', 'confmod', 'confadd', 'confok', 'confreptimeout', 'confrepfailed'],
    'confok': ['confdel', 'confmod', 'confadd', 'confok', 'confreptimeout', 'confrepfailed'],
    'confreptimeout': ['confdel', 'confmod', 'confadd', 'confok', 'confreptimeout', 'confrepfailed'],
    'confrepfailed': ['confdel', 'confmod', 'confadd', 'confok', 'confreptimeout', 'confrepfailed'],

    # monitor
    'monitorfail': ['monitorfail', 'monitorok'],
    'monitorok': ['monitorfail', 'monitorok'],

    # pools
    'poolnonodes': ['poolok', 'poolnonodes', 'pooldied'],
    'poolok': ['poolok', 'poolnonodes', 'pooldied'],
    'pooldied': ['poolok', 'poolnonodes', 'pooldied'],

    # nodes
    'nodeworking': ['nodeworking', 'nodefail'],
    'nodefail': ['nodeworking', 'nodefail'],

    # virtual servers
    'vsstart': ['vsstart', 'vsstop'],
    'vsstop': ['vsstart', 'vsstop'],

    # glb
    'glbmissingips': ['glbmissingips', 'glbdeadlocmissingips', 'glbnolocations', 'glbnewmaster', 'glblogwritefail', 'glbfailalter', 'glbservicedied', 'glbserviceok'],
    'glbdeadlocmissingips': ['glbmissingips', 'glbdeadlocmissingips', 'glbnolocations', 'glbnewmaster', 'glblogwritefail', 'glbfailalter', 'glbservicedied', 'glbserviceok'],
    'glbnolocations': ['glbmissingips', 'glbdeadlocmissingips', 'glbnolocations', 'glbnewmaster', 'glblogwritefail', 'glbfailalter', 'glbservicedied', 'glbserviceok'],
    'glbnewmaster': ['glbmissingips', 'glbdeadlocmissingips', 'glbnolocations', 'glbnewmaster', 'glblogwritefail', 'glbfailalter', 'glbservicedied', 'glbserviceok'],
    'glblogwritefail': ['glbmissingips', 'glbdeadlocmissingips', 'glbnolocations', 'glbnewmaster', 'glblogwritefail', 'glbfailalter', 'glbservicedied', 'glbserviceok'],
    'glbfailalter': ['glbmissingips', 'glbdeadlocmissingips', 'glbnolocations', 'glbnewmaster', 'glblogwritefail', 'glbfailalter', 'glbservicedied', 'glbserviceok'],
    'glbservicedied': ['glbmissingips', 'glbdeadlocmissingips', 'glbnolocations', 'glbnewmaster', 'glblogwritefail', 'glbfailalter', 'glbservicedied', 'glbserviceok'],
    'glbserviceok': ['glbmissingips', 'glbdeadlocmissingips', 'glbnolocations', 'glbnewmaster', 'glblogwritefail', 'glbfailalter', 'glbservicedied', 'glbserviceok'],
}

correlate = ZXTM_CORRELATED_EVENTS.get(event, list())

value = full_log_line[0]

if value == 'SERIOUS':
    severity = 'major'
elif value == 'WARN':
    severity = 'warning'
else:
    severity = 'normal'

text = full_log_line[-1]
