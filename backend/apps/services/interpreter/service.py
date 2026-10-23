import json
from asyncio import gather
from datetime import date, timedelta
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from apps.services.interpreter.calculation import calculation_evidence, plan_calculation
from apps.services.interpreter.context import Evidence, current_claims, prompt_context, sources
from apps.services.interpreter.drafting import BuildNotes, Draft, build_card, with_quotes
from apps.services.interpreter.followup import (
    checked_followup,
    cited_house_view,
    followup_evidence,
    followup_payload,
    original_card,
    trace_news,
)
from apps.services.interpreter.journal import Journal, utc_now
from apps.services.interpreter.planning import Plan, PlanConfig, Template
from apps.services.interpreter.prefilter import Prefilter, news_claims
from apps.services.interpreter.prompts import (
    DRAFT_SYSTEM,
    FOLLOWUP_DRAFT_SYSTEM,
    FOLLOWUP_PLAN_SYSTEM,
    PLAN_SYSTEM,
)
from shared.config.house_view_topics import HOUSE_VIEW_SUBJECTS
from shared.contracts.errors import BudgetExceeded, DomainError, NotFound
from shared.contracts.ports import (
    CounterpartyService,
    Critic,
    HouseViewService,
    LLMGateway,
    NewsService,
    ProfileService,
    TraceStore,
    WhatIfService,
)
from shared.contracts.schemas import (
    ActionContext,
    ClientProfile,
    CounterpartyContext,
    DashboardContext,
    FollowupContext,
    HouseViewClaim,
    InsightCard,
    InterpretRequest,
    InterpretResponse,
    NewsItem,
    PageContext,
    PaymentContext,
    Trace,
    TraceStep,
    WhatIfResult,
)


class Agent:
    def __init__(
        self,
        profiles: ProfileService,
        counterparties: CounterpartyService,
        news: NewsService,
        house_view: HouseViewService,
        whatif: WhatIfService,
        llm: LLMGateway,
        traces: TraceStore,
        critic: Critic,
        config: PlanConfig,
        threshold: float,
        model: str,
        followup_model: str,
    ) -> None:
        self._profiles = profiles
        self._counterparties = counterparties
        self._news = news
        self._house_view = house_view
        self._whatif = whatif
        self._llm = llm
        self._traces = traces
        self._critic = critic
        self._config = config
        self._model = model
        self._followup_model = followup_model
        self._prefilter = Prefilter(news, house_view, threshold=threshold)

    async def interpret(self, request: InterpretRequest) -> InterpretResponse:
        if isinstance(request.action_context, FollowupContext):
            checked = checked_followup(request.action_context, self._config.max_question_chars)
            request = request.model_copy(update={"action_context": checked})
        trace = Trace(
            id=str(uuid4()),
            request=request,
            steps=[],
            critic_verdicts=[],
            result=None,
            created_at=utc_now(),
        )
        followup = isinstance(request.action_context, FollowupContext)
        journal = Journal(
            trace,
            self._llm,
            "followup" if followup else "interpret",
            self._followup_model if followup else self._model,
            self._config.trace_summary_chars,
        )
        try:
            response = await self._run(request, journal)
        except Exception as error:
            trace.steps.append(
                TraceStep(
                    step="final",
                    name="failed",
                    input_summary="",
                    output_summary=type(error).__name__,
                    started_at=utc_now(),
                )
            )
            await self._traces.save(trace)
            if isinstance(error, ValidationError):
                raise DomainError("Interpreter received invalid structured model output") from error
            raise
        trace.result = response
        trace.steps.append(
            TraceStep(
                step="final",
                name="silent" if response.silent else "card",
                input_summary="",
                output_summary=f"{len(response.cards)} cards",
                started_at=utc_now(),
            )
        )
        await self._traces.save(trace)
        return response

    async def _run(self, request: InterpretRequest, journal: Journal) -> InterpretResponse:
        if isinstance(request.action_context, FollowupContext):
            return await self._followup(request, request.action_context, journal)
        template = self._config.templates.get(request.action_context.type)
        if template is None:
            raise DomainError(f"Unsupported interpreter workflow: {request.action_context.type}")
        profile = await journal.tool(
            "profile.get_profile",
            "authorized client features",
            self._profiles.get_profile(request.user_id, request.client_id),
        )
        counterparty = await self._counterparty(journal, request)
        as_of = journal.trace.created_at.date()
        pasted = await self._pasted_news(request, journal)
        prefilter_started_at = utc_now()
        start = perf_counter()
        feed = isinstance(request.action_context, DashboardContext)
        if pasted is None:
            limit = self._config.feed_search_limit if feed else self._config.search_limit
            scope = f"limit={limit}"
            selection = await self._prefilter.select(
                profile,
                request.action_context,
                counterparty,
                since=as_of - timedelta(days=self._config.lookback_days),
                as_of=as_of,
                limit=limit,
                subjects=template.house_view_subjects,
            )
        else:
            scope = f"pasted={pasted.id}"
            selection = await self._prefilter.rank(
                [pasted],
                profile,
                request.action_context,
                counterparty,
                as_of=as_of,
                subjects=template.house_view_subjects,
            )
        journal.trace.steps.append(
            TraceStep(
                step="prefilter",
                name="relevance",
                input_summary=scope,
                output_summary=json.dumps(
                    {
                        "candidates": [c.news.id for c in selection.candidates],
                        "house_view": [c.id for c in selection.house_view],
                    }
                ),
                duration_ms=int((perf_counter() - start) * 1000),
                started_at=prefilter_started_at,
            )
        )
        if not selection.candidates:
            return InterpretResponse(
                silent=True, silent_reason="Нет значимых событий для этого действия"
            )
        house_view = selection.house_view
        calculation = await self._calculation(journal, request.action_context, house_view, as_of)
        news = [candidate.news for candidate in selection.candidates]
        groups = [[item] for item in news[: self._config.feed_cards]] if feed else [news]
        results = await gather(
            *(
                self._card(
                    journal,
                    request,
                    template,
                    profile,
                    group,
                    news_claims(group, house_view, template.house_view_subjects),
                    as_of,
                    counterparty=counterparty,
                    calculation=calculation,
                    critic_view=house_view,
                )
                for group in groups
            ),
            return_exceptions=True,
        )
        cards = [result for result in results if isinstance(result, InsightCard)]
        failures = [result for result in results if isinstance(result, BaseException)]
        fatal = [
            error
            for error in failures
            if isinstance(error, BudgetExceeded)
            or not isinstance(error, DomainError | ValidationError)
        ]
        if fatal or not cards:
            raise (fatal or failures)[0]
        return InterpretResponse(
            silent=False, cards=sorted(cards, key=lambda card: -card.significance)
        )

    async def _card(
        self,
        journal: Journal,
        request: InterpretRequest,
        template: Template,
        profile: ClientProfile,
        news: list[NewsItem],
        house_view: list[HouseViewClaim],
        as_of: date,
        *,
        counterparty: CounterpartyContext | None,
        calculation: WhatIfResult | None,
        critic_view: list[HouseViewClaim],
    ) -> InsightCard:
        evidence = {
            **sources(profile, counterparty, news, house_view),
            **calculation_evidence(calculation),
        }
        plan = await self._plan(
            journal,
            PLAN_SYSTEM,
            template.model_dump(),
            {"context": prompt_context(request, profile, counterparty, evidence)},
        )
        current = await self._collect(journal, plan, house_view, as_of)
        evidence = {
            **sources(profile, counterparty, news, current),
            **calculation_evidence(calculation),
        }
        payload: dict[str, object] = {
            "plan": plan.model_dump(),
            "context": prompt_context(request, profile, counterparty, evidence),
        }
        draft = await journal.generate(
            "draft", DRAFT_SYSTEM, json.dumps(payload, ensure_ascii=False), Draft, journal.summary
        )
        checked = {claim.id: claim for claim in [*critic_view, *current]}
        card = await self._reviewed(
            journal,
            DRAFT_SYSTEM,
            payload,
            draft,
            evidence,
            [checked[key] for key in sorted(checked)],
            news,
        )
        return card.model_copy(update={"calculation": calculation})

    async def _followup(
        self, request: InterpretRequest, action: FollowupContext, journal: Journal
    ) -> InterpretResponse:
        original = await self._card_trace(journal, request, action.card_id)
        card = original_card(original, action.card_id)
        root = await self._root_request(journal, request, original)
        profile = await journal.tool(
            "profile.get_profile",
            "authorized client features",
            self._profiles.get_profile(request.user_id, request.client_id),
        )
        counterparty = await self._counterparty(journal, root)
        as_of = journal.trace.created_at.date()
        cited: dict[str, HouseViewClaim] = {}
        for claim_id in cited_house_view(card):
            cited.update({claim.id: claim for claim in await self._cited(journal, claim_id, as_of)})
        house_view = [cited[key] for key in sorted(cited)]
        prompt_request = root.model_copy(update={"role": request.role})
        plan = await self._plan(
            journal,
            FOLLOWUP_PLAN_SYSTEM,
            {"focus": self._config.followup_focus},
            followup_payload(
                action.question,
                prompt_request,
                card,
                profile,
                counterparty,
                followup_evidence(card, profile, counterparty, house_view),
            ),
        )
        current = await self._collect(journal, plan, house_view, as_of)
        evidence = followup_evidence(card, profile, counterparty, current)
        payload: dict[str, object] = {
            "plan": plan.model_dump(),
            **followup_payload(
                action.question, prompt_request, card, profile, counterparty, evidence
            ),
        }
        draft = await journal.generate(
            "draft",
            FOLLOWUP_DRAFT_SYSTEM,
            json.dumps(payload, ensure_ascii=False),
            Draft,
            journal.summary,
        )
        answer = await self._reviewed(
            journal, FOLLOWUP_DRAFT_SYSTEM, payload, draft, evidence, current, trace_news(card)
        )
        return InterpretResponse(silent=False, cards=[answer])

    async def _plan(
        self,
        journal: Journal,
        system: str,
        template: dict[str, object],
        context: dict[str, object],
    ) -> Plan:
        return await journal.generate(
            "plan",
            system,
            json.dumps(
                {
                    "template": template,
                    **context,
                    "allowed_subjects": sorted(HOUSE_VIEW_SUBJECTS),
                    "max_tool_calls": self._config.max_tool_calls,
                },
                ensure_ascii=False,
            ),
            Plan,
            lambda plan: journal.summary({"template": template, **plan.model_dump()}),
        )

    async def _card_trace(self, journal: Journal, request: InterpretRequest, card_id: str) -> Trace:
        return await journal.lookup(
            "trace.find_by_card",
            "trace of the questioned card",
            self._traces.find_by_card(
                user_id=request.user_id, client_id=request.client_id, card_id=card_id
            ),
            lambda trace: trace.id,
        )

    async def _root_request(
        self, journal: Journal, request: InterpretRequest, trace: Trace
    ) -> InterpretRequest:
        for _ in range(self._config.max_followup_depth):
            if not isinstance(trace.request.action_context, FollowupContext):
                return trace.request
            trace = await self._card_trace(journal, request, trace.request.action_context.card_id)
        if isinstance(trace.request.action_context, FollowupContext):
            raise DomainError(
                f"Followup chain is longer than {self._config.max_followup_depth} questions; "
                "ask about the original card"
            )
        return trace.request

    async def _counterparty(
        self, journal: Journal, request: InterpretRequest
    ) -> CounterpartyContext | None:
        if not isinstance(request.action_context, PaymentContext):
            return None
        action = request.action_context
        return await journal.tool(
            "counterparty.context",
            "recipient aggregates",
            self._counterparties.context(request.client_id, action.beneficiary_id, action.inn),
        )

    async def _cited(self, journal: Journal, claim_id: str, as_of: date) -> list[HouseViewClaim]:
        try:
            return await self._chain(journal, claim_id, as_of)
        except NotFound:
            return []

    async def _chain(self, journal: Journal, claim_id: str, as_of: date) -> list[HouseViewClaim]:
        batch = await journal.tool(
            "house_view.chain", claim_id, self._house_view.chain(claim_id=claim_id)
        )
        return current_claims(batch, as_of)

    async def _collect(
        self, journal: Journal, plan: Plan, house_view: list[HouseViewClaim], as_of: date
    ) -> list[HouseViewClaim]:
        plan.validate_tools(self._config, house_view)
        collected = {claim.id: claim for claim in house_view}
        for call in plan.tools:
            if call.tool == "house_view.claims":
                batch = await journal.tool(
                    call.tool,
                    call.argument,
                    self._house_view.claims(subject=call.argument, as_of=as_of),
                )
                found = current_claims(
                    [claim for claim in batch if claim.subject == call.argument], as_of
                )
            else:
                found = await self._chain(journal, call.argument, as_of)
            collected.update({claim.id: claim for claim in found})
        return [collected[key] for key in sorted(collected)]

    async def _calculation(
        self, journal: Journal, action: ActionContext, house_view: list[HouseViewClaim], as_of: date
    ) -> WhatIfResult | None:
        calculation = plan_calculation(action, house_view, as_of, self._config.loan_horizon_months)
        if calculation is None:
            return None
        return await journal.tool(
            f"whatif.{calculation.name}", calculation.summary, calculation.run(self._whatif)
        )

    async def _pasted_news(self, request: InterpretRequest, journal: Journal) -> NewsItem | None:
        if not isinstance(request.action_context, PageContext):
            return None
        text = request.action_context.text.strip()
        if not text:
            raise DomainError("Page text is empty")
        first, _, rest = text.partition("\n")
        first = first.rstrip()
        limit = self._config.max_title_chars
        body = rest.strip() if len(first) <= limit else text
        return await journal.tool(
            "news.annotate",
            "pasted page text",
            self._news.annotate(first[:limit].rstrip(), body, request.action_context.url),
        )

    def _build(
        self,
        journal: Journal,
        round_number: int,
        draft: Draft,
        evidence: dict[str, Evidence],
        card_id: str,
    ) -> tuple[InsightCard, BuildNotes]:
        trace_id = journal.trace.id
        limit = self._config.min_quote_words
        return journal.build(
            round_number, lambda: build_card(draft, evidence, card_id, trace_id, limit)
        )

    async def _reviewed(
        self,
        journal: Journal,
        system: str,
        payload: dict[str, object],
        draft: Draft,
        evidence: dict[str, Evidence],
        house_view: list[HouseViewClaim],
        news: list[NewsItem],
    ) -> InsightCard:
        card, notes = self._build(journal, 1, draft, evidence, str(uuid4()))
        round_number = 1
        try:
            verdicts = await journal.review(
                round_number, self._critic, card, house_view, news, notes
            )
            if not verdicts:
                return card
            round_number = 2
            previous = with_quotes(draft, evidence).model_dump()
            redraft = await journal.generate(
                "redraft",
                system,
                json.dumps(
                    {**payload, "previous_draft": previous, "critic_verdicts": verdicts},
                    ensure_ascii=False,
                ),
                Draft,
                journal.summary,
            )
            card, notes = self._build(journal, round_number, redraft, evidence, card.id)
            verdicts = await journal.review(
                round_number, self._critic, card, house_view, news, notes
            )
        except (DomainError, ValidationError) as error:
            journal.trace.critic_verdicts.append(f"{round_number}: error: {type(error).__name__}")
            return card.model_copy(update={"needs_review": True})
        return card.model_copy(update={"needs_review": bool(verdicts)})
