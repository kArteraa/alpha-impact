from shared.contracts.errors import ChargedModelError, DomainError


class ModelUnavailable(ChargedModelError):
    def __init__(
        self,
        message: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_rub: float | None = 0.0,
    ) -> None:
        super().__init__(message, tokens_in, tokens_out, cost_rub or 0.0)
        self.cost_known = cost_rub is not None


class ModelOutputInvalid(ChargedModelError):
    pass


class UsageNotRecorded(DomainError):
    pass


class CacheNotWritten(DomainError):
    pass
