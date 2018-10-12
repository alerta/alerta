import logging
import os

import requests

from alerta.plugins import PluginBase, app

LOG = logging.getLogger('alerta.plugins.gitlab')

GITLAB_URL = 'https://gitlab.com/api/v4'
GITLAB_PROJECT_ID = os.environ.get('GITLAB_PROJECT_ID', None) or app.config['GITLAB_PROJECT_ID']
GITLAB_ACCESS_TOKEN = os.environ.get('GITLAB_PERSONAL_ACCESS_TOKEN') or app.config['GITLAB_PERSONAL_ACCESS_TOKEN']


class GitlabIssue(PluginBase):

    def pre_receive(self, alert):
        return alert

    def post_receive(self, alert):
        return alert

    def status_change(self, alert, status, text):
        return alert, status, text

    def take_action(self, alert, action, text):
        """should return internal id of external system"""
        if action == 'createIssue':
            url = '{}/projects/{}/issues?title=foo'.format(GITLAB_URL, GITLAB_PROJECT_ID)
            r = requests.post(url, headers={'Private-Token': GITLAB_ACCESS_TOKEN})
            issue_id = r.json().get('id', None)
            alert.attributes['actionId'] = issue_id

        return alert, action, text
