#!/usr/bin/python

import os
import sys

import yaml

#rootdir = sys.argv[1]
rootdir = '/home/nsatterl/git/puppet/hieradata'

ping_list = list()
for root, subFolders, files in os.walk(rootdir):
    for f in files:
        full_path = os.path.join(root, f)

        if f == 'common.yaml':
            continue

        if 'aolpub' in full_path:
            service = ['R1']
        elif 'ora' in full_path:
            service = ['R2']
        elif 'ora' in full_path:
            service = ['R2']
        elif 'contentapi' in full_path:
            service = ['ContentAPI']
        elif 'ctldom' in full_path:
            service = ['Common']
        elif 'access' in full_path:
            service = ['Common']
        elif 'guadm' in full_path:
            service = ['SharedSvcs']
        elif 'dis' in full_path:
            service = ['Discussion']
        elif 'flexible' in full_path:
            service = ['FlexibleContent']
        elif 'gufed' in full_path:
            service = ['R2']
        elif 'guweb' in full_path:
            service = ['SharedSvcs']
        elif 'idapi' in full_path or 'idpub' in full_path or 'idprv' in full_path:
            service = ['Identity']
        elif 'ios' in full_path:
            service = ['Mobile']
        elif 'map' in full_path:
            service = ['R2']
        elif 'mng' in full_path:
            service = ['SharedSvcs']
        elif 'pgres' in full_path:
            service = ['Discussion']
        elif 'res' in full_path:
            service = ['R2']
        elif 'dns' in full_path:
            service = ['Common']
        elif 'rshsmt' in full_path:
            service = ['Common']
        elif 'ipbld' in full_path:
            service = ['Mobile']
        elif 'prx' in full_path:
            service = ['Common']
        elif 'smc' in full_path:
            service = ['Common']
        elif 'tmc' in full_path:
            service = ['SharedSvcs']
        elif 'gen' in full_path:
            service = ['Common']
        elif 'guddm' in full_path:
            service = ['R2']
        elif 'pup' in full_path:
            service = ['Common']
        elif 'ldom' in full_path:
            service = ['Common']
        elif 'auto' in full_path:
            service = ['R2']
        elif 'dns' in full_path:
            service = ['Common']
        else:
            service = ['UNKNOWN']


        hiera = yaml.load(open(full_path))
        print f
        if 'CODE' in full_path:
            environment = ['CODE']
        elif 'GUDEV' in full_path:
            environment = ['DEV']
        elif 'GUSTAGE' in full_path:
            environment = ['STAGE']
        elif 'INFRA' in full_path:
            environment = ['INFRA']
        elif 'LWP' in full_path:
            environment = ['LWP']
        elif 'PERF' in full_path:
            environment = ['PERF']
        elif 'PROD' in full_path:
            environment = ['PROD']
        elif 'QA' in full_path:
            environment = ['QA']
        elif 'RELEASE' in full_path:
            environment = ['RELEASE']
        elif 'STAGE' in full_path:
            environment = ['STAGE']
        elif 'TEST' in full_path:
            environment = ['TEST']
        elif 'sysctldom' in f:
            environment = ['INFRA']
        else:
            environment = ['UNKNOWN']

        if 'ganglia_agent_unicast_ip' in hiera and ('DEV' in environment or 'INFRA' in environment):
            ping_list.append({'service': service, 'environment': environment, 'targets': hiera['ganglia_agent_unicast_ip']})

print '---'
print yaml.dump(ping_list, default_flow_style=False)
