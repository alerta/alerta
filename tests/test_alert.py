from alerta.alert import Alert, severity

# TODO(nsatterl): make this a nose test
if __name__ == '__main__':
    alert1 = Alert('host555', 'ping_fail')
    print alert1

    alert2 = Alert('http://www.guardian.co.uk', 'HttpResponseSlow', ['HttpResponseOK','HttpResponseSlow'],
                   'HTTP', '505 ms', severity.CRITICAL, ['RELEASE', 'QA'],
                   ['gu.com'], 'The website is slow to respond.', 'httpAlert', ['web','dc1','user'],
                   'python-webtest', 'n/a', 1200)
    print alert2

    alert3 = Alert('router55', 'Node_Down', severity=severity.INDETERMINATE, value='FAILED', timeout=600,
                   service=['Network', 'Common'], tags=['london', 'location:london', 'dc:location=london'],
                   text="Node is not responding via ping.", origin="test3", correlate=['Node_Up', 'Node_Down'],
                   event_type='myAlert')
    print alert3


    print alert4