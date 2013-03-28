#
# OracelEMParser.py
#
# @param dict trapvars
#   $3 is the SNMP trap text
#
# @return string resource
#   database instance
# @return string severity
#   oraEM4AlertSeverity
# @return string environment
#   PROD, DEV
# @return string event
#   oraEM4AlertMetricName
# @return string value
#   oraEM4AlertMetricValue
# @return string text
#   oraEM4AlertMessage
# @return array tags
#   oraEM4AlertTargetName=oraEM4AlertTargetType
#   host=oraEM4AlertHostName
# @return string threshold
#   oraEM4AlertRuleName

resource = trapvars['$3'].split('.',1)[0]

if trapvars['$10'] in ['Serious', 'Critical']:
    severity = 'critical'
elif trapvars['$10'] == 'Error':
    severity = 'minor'
elif trapvars['$10'] == 'Warning':
    severity = 'warning'
elif trapvars['$10'] in ['Clear', 'Normal']:
    severity = 'normal'
else:
    severity = 'informational'

if trapvars['$A'].endswith('gudev.gnl'):
    environment = 'DEV'
else:
    environment = 'PROD'

event = trapvars['$6'].replace(' ','')
value = trapvars['$14']
text = trapvars['$11']
tags.append('%s=%s' % (trapvars['$4'], trapvars['$3']))
tags.append('host=%s' % trapvars['$5'])
threshold = trapvars['$12']
