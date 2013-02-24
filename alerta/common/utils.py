"""Utilities and helper functions."""

import json
import datetime


class Bunch:
    """
    Usage: print Bunch({'a':1, 'b':{'foo':2}}).b.foo
    """
    def __init__(self):
        pass

    def Load(self, d):
        for k, v in d.items():
            if isinstance(v, dict):
                v = Bunch(v)
            self.__dict__[k] = v

    def __str__(self):
        state = ["%s=%r" % (attribute, value)
                 for (attribute, value)
                 in self.__dict__.items()]
        return '%s(%s)' % (self.__class__.__name__, state)


# Extend JSON Encoder to support ISO 8601 format dates
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        print 'obj=>%s' % obj
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.replace(microsecond=0).isoformat() + ".%03dZ" % (obj.microsecond // 1000)
        else:
            return json.JSONEncoder.default(self, obj)
