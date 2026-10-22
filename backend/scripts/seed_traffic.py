import argparse
import asyncio
import json
from collections import defaultdict

from apps.services.counterparty.config import load_config
from apps.services.counterparty.loader import read_payments
from apps.services.gateway.service import InterpretGateway
from main import build_container
from scripts.seed import RAW_DIR, SEED_DIR
from shared.contracts.errors import DomainError
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import InterpretRequest, PaymentContext, Role

UNKNOWN_COMPANY = "U_999999999"
PAYMENT_AMOUNT = 1_000_000.0


def seed_clients() -> dict[str, str]:
    users = json.loads((SEED_DIR / "users.json").read_text(encoding="utf-8"))
    return {client: user["id"] for user in users for client in user["clients"]}


def beneficiaries(clients: set[str], per_client: int) -> dict[str, list[str]]:
    paid: defaultdict[str, list[str]] = defaultdict(list)
    for payment in read_payments(RAW_DIR / load_config().payments_file):
        targets = paid[payment.payer]
        if payment.payer in clients and len(targets) < per_client:
            if payment.beneficiary not in targets:
                targets.append(payment.beneficiary)
    return {client: [*paid[client], UNKNOWN_COMPANY] for client in clients}


async def main(per_client: int) -> None:
    users = seed_clients()
    container = build_container()
    try:
        llm = container.resolve(LLMGateway)
        budget_before = await llm.budget_left_rub()
        gateway = container.resolve(InterpretGateway)
        cards = silent = failed = 0
        for client_id, targets in beneficiaries(set(users), per_client).items():
            for beneficiary_id in targets:
                request = InterpretRequest(
                    user_id=users[client_id],
                    client_id=client_id,
                    role=Role.CFO,
                    action_context=PaymentContext(
                        beneficiary_id=beneficiary_id, amount=PAYMENT_AMOUNT
                    ),
                )
                try:
                    response = await gateway.interpret(users[client_id], request)
                except DomainError as error:
                    failed += 1
                    print(f"{client_id} -> {beneficiary_id}: {type(error).__name__}")
                    continue
                cards += len(response.cards)
                silent += response.silent
                print(f"{client_id} -> {beneficiary_id}: {len(response.cards)} cards")
        spent = budget_before - await llm.budget_left_rub()
        print(f"cards: {cards}, silent: {silent}, failed: {failed}, spent: {spent:.4f} RUB")
    finally:
        await container.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-client", type=int, default=3)
    asyncio.run(main(parser.parse_args().per_client))
