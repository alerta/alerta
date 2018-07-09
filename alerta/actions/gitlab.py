import os
import logging
import requests

from alerta.actions import app
from alerta.actions import ActionBase

LOG = logging.getLogger('alerta.actions.gitlab')

GITLAB_URL = 'https://gitlab.com/api/v4'
GITLAB_PROJECT_ID = '7422767'
GITLAB_ACCESS_TOKEN=os.environ.get('GITLAB_PERSONAL_ACCESS_TOKEN')


class GitlabIssue(ActionBase):

    def take_action(self, alert, action, text):
        """should return internal id of external system"""

        if action=='issue':
            print('take action to create gitlab issue')

            url = '%s/projects/%s/issues?title=foo' % (GITLAB_URL, GITLAB_PROJECT_ID)
            r = requests.post(url, headers={'Private-Token': GITLAB_ACCESS_TOKEN})
            print(r.json())
            issue_id = r.json().get('id', None)
            alert.attributes = {'actionId': issue_id}
            return alert
        else:
            print('action ignored by gitlab action handler')
        return

    def update_alert(self, alert):
        # FIXME - handle updates to alert (eg. normal/ok/cleared)
        return alert
