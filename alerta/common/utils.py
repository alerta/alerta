"""Utilities and helper functions."""


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
