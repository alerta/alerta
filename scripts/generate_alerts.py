#!/usr/bin/env python
"""Generate random alerts for testing. Requires: pip install httpx"""

import argparse
import random
import sys
import time

import httpx

ENVIRONMENTS = ['Production', 'Development', 'Staging', 'QA']
SERVICES = [
    ['Web'], ['API'], ['Database'], ['Cache'], ['Queue'],
    ['Auth'], ['Search'], ['Storage'], ['Monitoring'], ['DNS'],
]
GROUPS = ['Infrastructure', 'Application', 'Network', 'Security', 'Performance']
RESOURCES = [
    'web-01', 'web-02', 'web-03', 'api-01', 'api-02',
    'db-primary', 'db-replica-01', 'db-replica-02',
    'cache-01', 'cache-02', 'queue-01', 'queue-02',
    'lb-01', 'lb-02', 'dns-01', 'nfs-01',
    'k8s-node-01', 'k8s-node-02', 'k8s-node-03', 'k8s-node-04',
]
EVENTS = {
    'Infrastructure': [
        ('HighCPU', ['10%', '25%', '50%', '75%', '90%', '95%', '99%']),
        ('HighMemory', ['60%', '70%', '80%', '90%', '95%']),
        ('DiskFull', ['80%', '85%', '90%', '95%', '98%']),
        ('HighLoad', ['2.0', '4.0', '8.0', '16.0', '32.0']),
        ('SwapUsage', ['10%', '25%', '50%', '75%']),
        ('HighIOWait', ['5%', '10%', '20%', '40%']),
    ],
    'Application': [
        ('HttpError5xx', ['500', '502', '503', '504']),
        ('HttpError4xx', ['400', '401', '403', '404', '429']),
        ('HighLatency', ['200ms', '500ms', '1s', '2s', '5s', '10s']),
        ('QueueBacklog', ['100', '500', '1000', '5000', '10000']),
        ('ConnectionPoolExhausted', ['90%', '95%', '100%']),
        ('DeploymentFailed', ['v1.2.3', 'v1.2.4', 'v2.0.0']),
    ],
    'Network': [
        ('PacketLoss', ['1%', '5%', '10%', '25%']),
        ('HighLatency', ['10ms', '50ms', '100ms', '500ms']),
        ('InterfaceDown', ['eth0', 'eth1', 'bond0']),
        ('BGPPeerDown', ['peer-1', 'peer-2', 'peer-3']),
        ('DNSResolutionFailure', ['timeout', 'NXDOMAIN', 'SERVFAIL']),
    ],
    'Security': [
        ('BruteForceAttempt', ['10/min', '50/min', '100/min']),
        ('SSLCertExpiring', ['7d', '3d', '1d', '12h']),
        ('UnauthorizedAccess', ['admin', 'api', 'ssh']),
        ('MalwareDetected', ['trojan', 'ransomware', 'cryptominer']),
    ],
    'Performance': [
        ('SlowQuery', ['1s', '5s', '10s', '30s']),
        ('CacheMissRate', ['10%', '25%', '50%', '75%']),
        ('GCPause', ['100ms', '500ms', '1s', '5s']),
        ('ThreadPoolExhausted', ['80%', '90%', '95%', '100%']),
        ('ReplicationLag', ['1s', '5s', '30s', '60s', '300s']),
    ],
}
SEVERITIES = ['critical', 'major', 'minor', 'warning', 'informational', 'normal']
SEVERITY_WEIGHTS = [5, 10, 20, 30, 20, 15]
TAGS_POOL = [
    'linux', 'windows', 'docker', 'k8s', 'aws', 'gcp',
    'us-east-1', 'eu-west-1', 'ap-southeast-1',
    'tier-1', 'tier-2', 'tier-3',
    'oncall', 'business-hours', 'p1', 'p2', 'p3',
    'auto-remediate', 'manual', 'reviewed',
]
ORIGINS = ['prometheus', 'grafana', 'cloudwatch', 'datadog', 'nagios', 'zabbix', 'custom-monitor']
TEXTS = [
    'Threshold exceeded',
    'Anomaly detected by ML model',
    'Triggered by scheduled health check',
    'Correlated with recent deployment',
    'Recurring issue, see runbook',
    'Transient spike detected',
    'Capacity planning threshold reached',
    'SLO breach imminent',
    'Dependency degradation detected',
    '',
]


def generate_alert():
    group = random.choice(GROUPS)
    event, values = random.choice(EVENTS[group])
    return {
        'resource': random.choice(RESOURCES),
        'event': event,
        'environment': random.choice(ENVIRONMENTS),
        'severity': random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS, k=1)[0],
        'service': random.choice(SERVICES),
        'group': group,
        'value': random.choice(values),
        'text': random.choice(TEXTS),
        'tags': random.sample(TAGS_POOL, k=random.randint(1, 4)),
        'origin': random.choice(ORIGINS),
        'attributes': {
            'region': random.choice(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']),
            'team': random.choice(['platform', 'sre', 'backend', 'infra', 'security']),
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Generate random alerts for Alerta')
    parser.add_argument('-n', '--count', type=int, default=1000, help='Number of alerts (default: 1000)')
    parser.add_argument('-u', '--url', default='http://localhost:8180', help='Alerta API URL')
    parser.add_argument('-k', '--api-key', default='', help='API key')
    parser.add_argument('--batch', type=int, default=50, help='Batch size for progress reporting')
    args = parser.parse_args()

    headers = {'Content-Type': 'application/json'}
    if args.api_key:
        headers['X-API-Key'] = args.api_key

    client = httpx.Client(base_url=args.url, headers=headers, timeout=30.0)

    created = 0
    errors = 0
    start = time.time()

    for i in range(args.count):
        alert = generate_alert()
        try:
            resp = client.post('/alert', json=alert)
            if resp.status_code in (200, 201, 202):
                created += 1
            else:
                errors += 1
                if errors <= 3:
                    print(f'  error: {resp.status_code} {resp.text[:100]}', file=sys.stderr)
        except httpx.HTTPError as e:
            errors += 1
            if errors <= 3:
                print(f'  error: {e}', file=sys.stderr)

        if (i + 1) % args.batch == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            print(f'  {i + 1}/{args.count} ({rate:.0f}/s) created={created} errors={errors}')

    elapsed = time.time() - start
    print(f'\nDone: {created} created, {errors} errors in {elapsed:.1f}s ({created / elapsed:.0f}/s)')


if __name__ == '__main__':
    main()
