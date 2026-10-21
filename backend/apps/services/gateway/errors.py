from collections.abc import Iterator
from contextlib import contextmanager

from fastapi import HTTPException, status

from shared.contracts.errors import AccessDenied, BudgetExceeded, DomainError, NotFound

STATUS_BY_ERROR: tuple[tuple[type[DomainError], int], ...] = (
    (AccessDenied, status.HTTP_403_FORBIDDEN),
    (NotFound, status.HTTP_404_NOT_FOUND),
    (BudgetExceeded, status.HTTP_503_SERVICE_UNAVAILABLE),
    (DomainError, status.HTTP_422_UNPROCESSABLE_CONTENT),
)


@contextmanager
def domain_errors() -> Iterator[None]:
    try:
        yield
    except DomainError as error:
        code = next(code for kind, code in STATUS_BY_ERROR if isinstance(error, kind))
        raise HTTPException(code, str(error)) from error
