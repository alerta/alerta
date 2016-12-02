
class AlertaException(IOError):
    pass

class RejectException(AlertaException):
    """The alert was rejected because the format did not meet the required policy."""
    pass

class RateLimit(AlertaException):
    """Too many alerts have been received for a resource or from an origin."""
    pass

class BlackoutPeriod(AlertaException):
    """Alert was not processed becauese it was sent during a blackout period."""
    pass
