class DomainError(Exception):
    pass


class AccessDenied(DomainError):
    pass


class NotFound(DomainError):
    pass


class BudgetExceeded(DomainError):
    pass


class ChargedModelError(DomainError):
    def __init__(
        self, message: str, tokens_in: int = 0, tokens_out: int = 0, cost_rub: float = 0.0
    ) -> None:
        super().__init__(message)
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_rub = cost_rub
