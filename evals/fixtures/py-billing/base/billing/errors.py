class BillingError(Exception):
    pass


class NotFound(BillingError):
    pass


class InvalidState(BillingError):
    pass


class InvalidRequest(BillingError):
    pass
