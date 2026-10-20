from shared.contracts.errors import DomainError


class ModelUnavailable(DomainError):
    pass


class ModelOutputInvalid(DomainError):
    pass
