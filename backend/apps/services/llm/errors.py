from shared.contracts.errors import DomainError


class ModelUnavailable(DomainError):
    def __init__(self, message: str, tokens_in: int = 0, tokens_out: int = 0) -> None:
        super().__init__(message)
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out


class ModelOutputInvalid(DomainError):
    pass
