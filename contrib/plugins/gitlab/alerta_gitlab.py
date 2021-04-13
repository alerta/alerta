import logging
import os
from urllib.parse import quote
from flask import g
import requests
import datetime

from alerta.plugins import PluginBase, app

LOG = logging.getLogger('alerta.plugins.gitlab')

GITLAB_URL = os.environ.get('GITLAB_URL', None) or app.config['GITLAB_URL']
GITLAB_PROJECT_ID = os.environ.get('GITLAB_PROJECT_ID', None) or app.config['GITLAB_PROJECT_ID']
GITLAB_ACCESS_TOKEN = os.environ.get('GITLAB_PERSONAL_ACCESS_TOKEN') or app.config['GITLAB_PERSONAL_ACCESS_TOKEN']


class GitlabIssue(PluginBase):

    def __init__(self, name=None):
        self.headers = {'Private-Token': GITLAB_ACCESS_TOKEN}
        super().__init__()

    def pre_receive(self, alert, **kwargs):
        for tag in alert.tags:
            try:
                k, v = tag.split('=', 1)
                if k == 'project_id':
                    alert.attributes['base_url'] = '{}/projects/{}'.format(GITLAB_URL, quote(v, safe=''))
            except ValueError:
                pass
        return alert

    def post_receive(self, alert, **kwargs):
        starttime = alert.create_time
        deadtime = starttime + datetime.timedelta(days=1)
        lastreceivedtime = alert.last_receive_time
        if (lastreceivedtime > deadtime):
            if 'issue_iid' not in alert.attributes:
                url = alert.attributes['base_url'] + '/issues?title=' + alert.text
                r = requests.post(url, headers=self.headers)
                alert.attributes['Open Issue User'] = g.login
                alert.attributes['gitlab_result'] = r.text
                alert.attributes['gitlab_status_code'] = r.status_code
                alert.attributes['issue_iid'] = r.json().get('iid', None)
                alert.attributes['gitlabUrl'] = '<a href="{}" target="_blank">Issue #{}</a>'.format(
                    r.json().get('web_url', None),
                    r.json().get('iid', None)
                )
                due = '/due in 1 days \n'
                assign = '/assign @all'
                issue_iid = alert.attributes['issue_iid']
                issue_body due + assign
                dueurl = alert.attributes['base_url'] + '/issues/{}/discussions?body={}'.format(issue_iid, issue_body)
                r1 = requests.post(dueurl, headers=self.headers)
        return alert

    def status_change(self, alert, status, text, **kwargs):
        return alert, status, text

    def take_action(self, alert, action, text, **kwargs):
        """should return internal id of external system"""

        if action == 'createIssue':
            if 'issue_iid' not in alert.attributes:
                url = alert.attributes['base_url'] + '/issues?title=' + alert.text
                r = requests.post(url, headers=self.headers)
                alert.attributes['Open Issue User'] = g.login
                alert.attributes['gitlab_result'] = r.text
                alert.attributes['gitlab_status_code'] = r.status_code
                alert.attributes['issue_iid'] = r.json().get('iid', None)
                alert.attributes['gitlabUrl'] = '<a href="{}" target="_blank">Issue #{}</a>'.format(
                    r.json().get('web_url', None),
                    r.json().get('iid', None)
                )
                due = '/due in 1 days \n'
                assign = '/assign @all'
                issue_iid = alert.attributes['issue_iid']
                issue_body due + assign
                dueurl = alert.attributes['base_url'] + '/issues/{}/discussions?body={}'.format(issue_iid, issue_body)
                r1 = requests.post(dueurl, headers=self.headers)

        elif action == 'updateIssue':
            if 'issue_iid' in alert.attributes:
                body = 'Update: ' + alert.text
                issue_iid = alert.attributes['issue_iid']
                url = alert.attributes['base_url'] + '/issues/{}/discussions?body={}'.format(issue_iid, body)
                r = requests.post(url, headers=self.headers)

        elif action == 'closeIssue':
            if 'issue_iid' in alert.attributes:
                issue_iid = alert.attributes['issue_iid']
                url = alert.attributes['base_url'] + '/issues/{}/notes?body=closed\n/close'.format(issue_iid)
                r = requests.post(url, headers=self.headers)

        return alert, action, text
