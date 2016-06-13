

def rules(alert, plugins):

    print alert

    if 'reject' in alert.text:
        return [plugins['reject']]
    else:
        return [plugins['normalise'], plugins['enhance']]
