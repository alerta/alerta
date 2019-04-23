"""
Example Routing Rules Plugin - Customer-based Escalation/Notification

Use different notification paths for different customers. ie. PagerDuty
for Tier 1 customers, Slack for Tier 2 and nothing for Tier 3 customers.
"""

TIER_ONE_CUSTOMERS = [
    'Tyrell Corporation',
    'Cyberdyne Systems',
    'Weyland-Yutani',
    'Zorin Enterprises'
]

TIER_TWO_CUSTOMERS = [
    'Soylent Corporation',
    'Omni Consumer Products',
    'Dolmansaxlil Shoe Corporation'
]


def rules(alert, plugins):

    if alert.customer in TIER_ONE_CUSTOMERS:
        # Tier 1 customer SLA needs PagerDuty to manage escalation
        return [
            plugins['reject'],
            plugins['blackout'],
            plugins['pagerduty']
        ], {'foo': 'bar'}
    elif alert.customer in TIER_TWO_CUSTOMERS:
        # Tier 2 customers handled via Slack
        return [
            plugins['reject'],
            plugins['blackout'],
            plugins['slack']
        ], {'baz', 'quux'}
    else:
        # Tier 3 customers get "best effort"
        return [
            plugins['reject'],
            plugins['blackout']
        ]
