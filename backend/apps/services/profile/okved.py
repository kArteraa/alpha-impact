OTHER = "other"


def normalize(code: str) -> str:
    parts = code.strip().split(".")
    if len(parts) > 1 and len(parts[1]) == 1:
        parts[1] += "0"
    return ".".join(parts)


def covers(prefix: str, code: str) -> bool:
    division, _, rest = prefix.partition(".")
    code_division, _, code_rest = code.partition(".")
    return division == code_division and code_rest.startswith(rest)


def industry_class(code: str, industries: dict[str, str]) -> str:
    matches = [prefix for prefix in industries if covers(prefix, code)]
    if not matches:
        return OTHER
    return industries[max(matches, key=len)]
