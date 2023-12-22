import unittest.mock as mock

import pytest

from alerta.exceptions import RejectException
from alerta.models.alert import Alert
from alerta.plugins.reject import RejectPolicy

TEST_ORIGIN_BLACKLISTS = []

TEST_ALLOWED_ENVIRONMENTS = [
    'test_env',
]


@pytest.fixture
def reject_policy():
    reject = RejectPolicy()

    def mock_get_config(name, default, type, **kwargs):
        if name == 'ORIGIN_BLACKLIST':
            return TEST_ORIGIN_BLACKLISTS
        elif name == 'ALLOWED_ENVIRONMENTS':
            return TEST_ALLOWED_ENVIRONMENTS
        raise Exception('Bad name')

    reject.get_config = mock.Mock(
        spec=RejectPolicy.get_config, side_effect=mock_get_config
    )
    return reject


def test_reject_policy_allowed(reject_policy):
    allowed_alert = Alert(
        'test_resource',
        'test_event',
        environment='test_env',
        timeout=5,
        service=['test_service'],
    )
    returned_alert = reject_policy.pre_receive(allowed_alert)
    assert returned_alert == allowed_alert


def test_reject_policy_rejected(reject_policy):
    reject_alerts = [
        Alert(
            'test_resource',
            'test_event',
            environment='prod',
            timeout=5,
            service=['test_service'],
        ),
        Alert(
            'test_resource',
            'test_event',
            environment='test',
            timeout=5,
            service=['test_service'],
        ),
        Alert(
            'test_resource',
            'test_event',
            environment='test_environment',
            timeout=5,
            service=['test_service'],
        ),
    ]

    for alert in reject_alerts:
        with pytest.raises(RejectException):
            reject_policy.pre_receive(alert)
