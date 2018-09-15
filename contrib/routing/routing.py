# Example plugin routing rules file


def rules(alert, plugins):

    if alert.severity == 'debug':
        return []
    else:
        return [plugins['reject']]
