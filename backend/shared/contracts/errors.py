class DomainError(Exception):
    pass


class AccessDenied(DomainError):
    pass


class NotFound(DomainError):
    pass


class BudgetExceeded(DomainError):
    pass
