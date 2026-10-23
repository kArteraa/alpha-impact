from datetime import UTC, date, datetime

from pydantic import BaseModel

from shared.contracts import schemas as s

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)

SOURCE = s.SourceRef(
    kind="news",
    id="news-1",
    title="ЦБ сохранил ключевую ставку",
    url="https://example.com/news/1",
    published_at=NOW,
)
CLAIM = s.Claim(text="Ставка 14% сохранена", type=s.ClaimType.FACT, source_ref=SOURCE)
OFFER = s.ProductOffer(
    product="letter_of_credit", reason="Отрасль получателя в стрессе", rule_id="r1"
)
CALCULATION = s.WhatIfResult(
    kind="rate_burden",
    value=-290_000.0,
    unit="RUB",
    formula="50 000 000 ₽ × (13,42% − 14%) × 12/12 мес. = −290 000 ₽",
    assumptions=["спред к ключевой ставке не меняется"],
)
CARD = s.InsightCard(
    id="card-1",
    headline="Логистика в убытке",
    what_happened=[CLAIM],
    why_for_you=[CLAIM],
    consequences=[CLAIM],
    actions=[CLAIM],
    bank_view=[CLAIM],
    basis=[SOURCE],
    product_offer=OFFER,
    calculation=CALCULATION,
    significance=0.8,
    trace_id="trace-1",
)
PAYMENT = s.PaymentContext(amount=1_500_000.0, beneficiary_id="cp_logistics_spb")
REQUEST = s.InterpretRequest(user_id="u1", client_id="c1", role=s.Role.CFO, action_context=PAYMENT)
RESPONSE = s.InterpretResponse(silent=False, cards=[CARD])
FEATURE = s.Feature(value=["CN", "TR"], source="graph", confidence=0.7, updated_at=NOW)
FACTOR = s.Factor(name="logistics_margin", direction="down", strength=0.6, horizon="quarter")
STEP = s.TraceStep(
    step="plan",
    name="plan_payment",
    input_summary="payment to cp_logistics_spb",
    output_summary="3 tools",
    model="glm-5.3-flash",
    tokens_in=120,
    tokens_out=40,
    cost_rub=0.03,
    duration_ms=850,
    started_at=NOW,
)
TRACE = s.Trace(
    id="trace-1",
    request=REQUEST,
    steps=[STEP],
    critic_verdicts=["ok"],
    result=RESPONSE,
    created_at=NOW,
)

EXAMPLES: dict[type[BaseModel], BaseModel] = {
    s.PaymentContext: PAYMENT,
    s.DepositContext: s.DepositContext(amount=5_000_000.0, term_days=90),
    s.FxContext: s.FxContext(currency="USD", country="CN", amount=10_000.0),
    s.LoanContext: s.LoanContext(product="loan", amount=100_000_000.0, rate_type="floating"),
    s.PayrollContext: s.PayrollContext(headcount=120, amount=20_000_000.0),
    s.DashboardContext: s.DashboardContext(),
    s.PageContext: s.PageContext(url="https://example.com/a", text="Текст", entities=["логистика"]),
    s.FollowupContext: s.FollowupContext(card_id="card-1", question="А если ставку снизят?"),
    s.InterpretRequest: REQUEST,
    s.SourceRef: SOURCE,
    s.Claim: CLAIM,
    s.ProductOffer: OFFER,
    s.InsightCard: CARD,
    s.InterpretResponse: RESPONSE,
    s.Feature: FEATURE,
    s.ClientProfile: s.ClientProfile(
        client_id="c1",
        group_id="g1",
        group_members=["c1", "c2"],
        features={"import_countries": FEATURE},
        exposures={"rate": 0.6},
        flags={"has_leasing": True},
        version=1,
    ),
    s.CounterpartyContext: s.CounterpartyContext(
        industry_class="logistics",
        region="spb",
        size_bucket="large",
        share_of_client_outflow=0.43,
        share_of_counterparty_inflow=0.1,
        confidence=0.9,
    ),
    s.Factor: FACTOR,
    s.NewsItem: s.NewsItem(
        id="news-1",
        title="Склады маркетплейсов под ударом",
        text="Текст новости",
        url="https://example.com/news/1",
        published_at=NOW,
        source="kommersant",
        entities=["логистика"],
        factors=[FACTOR],
    ),
    s.HouseViewClaim: s.HouseViewClaim(
        id="hv-1",
        claim="Ставка 14% до конца 2026",
        type="forecast",
        subject="rate",
        value="14",
        date=date(2026, 9, 11),
        valid_until=date(2026, 12, 31),
        source_doc="macro_2026_09_11.pdf",
        page=3,
        superseded_by=None,
        status="approved",
    ),
    s.WhatIfResult: s.WhatIfResult(
        kind="rate_burden",
        value=1_200_000.0,
        unit="RUB",
        formula="amount * (rate_expected - rate_now) / 100 * months / 12",
        assumptions=["ставка меняется сразу"],
    ),
    s.TraceStep: STEP,
    s.Trace: TRACE,
}
