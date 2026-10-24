from prometheus_client import Counter

OK = "ok"
CACHE = "cache"
CALLS = Counter("llm_calls", "Model calls by task, model and outcome", ["task", "model", "outcome"])
TOKENS = Counter("llm_tokens", "Tokens charged by the model proxy", ["task", "model", "direction"])
COST_RUB = Counter("llm_cost_rub", "Rubles charged by the model proxy", ["task", "model"])


def count_call(task: str, model: str, outcome: str) -> None:
    CALLS.labels(task, model, outcome).inc()


def count_spend(task: str, model: str, tokens_in: int, tokens_out: int, cost_rub: float) -> None:
    TOKENS.labels(task, model, "in").inc(tokens_in)
    TOKENS.labels(task, model, "out").inc(tokens_out)
    COST_RUB.labels(task, model).inc(cost_rub)
