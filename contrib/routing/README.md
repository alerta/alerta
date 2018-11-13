Example plugin routing rules
============================

If severity is "debug" do not apply the "reject" policy to enforce a valid environment and a service.

```python
def rules(alert, plugins):

    if alert.severity == 'debug':
        return []
    else:
        return [plugins['reject']]
```

Installation
------------

    $ python setup.py install
