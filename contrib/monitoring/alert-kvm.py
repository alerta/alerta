#!/usr/bin/env python

import os
import subprocess
import re

"""
 Id    Name                           State
----------------------------------------------------
 6     instance-00000654              running
 7     instance-00000655              running
 9     instance-00000657              running
 10    instance-00000658              running
"""


def main():

    cmd = "/usr/bin/virsh list"
    virsh_list = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout = virsh_list.communicate()[0].rstrip('\n')

    for line in stdout.split('\n'):
        m = re.match('\s+\d+\s+instance-(?P<instance_id>\S+)\s+(?P<state>\S+)', line)
        if m:
            instance_id = 'i-' + m.group('instance_id')
            state = m.group('state')

            if state == 'running':
                severity = 'normal'
            else:
                severity = 'major'

            cmd = ('alert-sender --resource {instance_id} --group GWS/GC2 --event Gc2InstanceState --value {state} '
                   '--severity {severity} --environment INFRA --service OpenStack --text "Instance is {state}" '
                   '--origin alert-kvm').format(instance_id=instance_id, severity=severity, state=state)
            #print cmd
            os.system(cmd)

if __name__ == '__main__':
    main()
