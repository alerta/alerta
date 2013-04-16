#!/usr/bin/env python

import sys
import re
import yaml

try:
    ping = dict()

    environment = 'INFRA'
    service = 'Common'

    for line in sys.stdin:

        print 'env = %s, svc = %s, line = %s' % (environment, service, line)

        if 'CNAME' in line:
            continue

        if ';' in line:
            if 'PROD' in line.upper():
                environment = 'PROD'
            elif 'REL' in line.upper():
                environment = 'RELEASE'
            elif 'QA' in line.upper():
                environment = 'QA'
            elif 'PERF' in line.upper():
                environment = 'PERF'
            elif 'DEV' in line.upper():
                environment = 'DEV'
            elif 'TEST' in line.upper():
                environment = 'TEST'
            elif 'LWP' in line.upper():
                environment = 'LWP'

            m = re.search(r'service=(?P<svc>\S+)', line)
            if m:
                service = m.group('svc')

        else:
            m = re.search(r'(\S+)\s+IN A\s+(\S+)', line)
            if m:
                host = m.group(1)
                if (environment, service) in ping:
                    ping[(environment, service)].append(host)
                else:
                    ping[(environment, service)] = [host]

            else:
                #print '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>' + line,
                pass

except KeyboardInterrupt:
    sys.stdout.flush()

print '---'
for environment, service in ping:
    targets = [{"environment": environment, "service": service, "targets": ping[(environment, service)]}]
    print yaml.dump(targets, default_flow_style=False)

