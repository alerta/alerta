"""Utilities and helper functions."""

class Bunch:
    def __init__(self):
        pass

    def Load(self, d):
        for k, v in d.items():
            if isinstance(v, dict):
                v = Bunch(v)
            self.__dict__[k] = v