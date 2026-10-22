import json
from datetime import date, timedelta
from time import perf_counter
from uuid import uuid4

from pydantic import ValidationError

from apps.services.interpreter.context import Evidence, current_claims, prompt_context, sources
from apps.services.interpreter.drafting import Draft, build_card
from apps.services.interpreter.followup import (
    cited_house_view,
    followup_evidence,
    followup_payload,
    original_card,
    trace_news,
)
from apps.services.interpreter.journal import Journal, utc_now
from apps.services.interpreter.planning import Plan, PlanConfig
from apps.services.interpreter.prefilter import Prefilter
from apps.services.interpreter.prompts import (
    DRAFT_SYSTEM,
    FOLLOWUP_DRAFT_SYSTEM,
    FOLLOWUP_PLAN_SYSTEM,
    PLAN_SYSTEM,
)
from shared.config.factors import FACTORS
from shared.contracts.errors import DomainError
from shared.contracts.ports import (
    CounterpartyService,
    Critic,
    HouseViewService,
    LLMGateway,
    NewsService,
    ProfileService,
    TraceStore,
)
from shared.contracts.schemas import (
    FollowupContext,
    HouseViewClaim,
    InsightCard,
    InterpretRequest,
    InterpretResponse,
    NewsItem,
    PaymentContext,
    Trace,
    TraceStep,
)


class Agent:
    def __init__(
        self,
        profiles: ProfileService,
        counterparties: CounterpartyService,
        news: NewsService,
        house_view: HouseViewService,
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
        self._house_view = house_view
        self._llm = llm
        self._traces = traces
        self._critic = critic
        self._config = config
        self._model = model
        self._followup_model = followup_model
        self._prefilter = Prefilter(news, house_view, threshold=threshold)

    async def interpret(self, request: InterpretRequest) -> InterpretResponse:
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
        counterparty = None
        if isinstance(request.action_context, PaymentContext):
            action = request.action_context
            counterparty = await journal.tool(
                "counterparty.context",
                "recipient aggregates",
                self._counterparties.context(request.client_id, action.beneficiary_id, action.inn),
            )
        as_of = journal.trace.created_at.date()
        prefilter_started_at = utc_now()
        start = perf_counter()
        selection = await self._prefilter.select(
            profile,
            request.action_context,
            counterparty,
            since=as_of - timedelta(days=self._config.lookback_days),
            as_of=as_of,
            limit=self._config.search_limit,
        )
        journal.trace.steps.append(
            TraceStep(
                step="prefilter",
                name="relevance",
                input_summary=f"limit={self._config.search_limit}",
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
        news = [candidate.news for candidate in selection.candidates]
        house_view = selection.house_view
        evidence = sources(profile, counterparty, news, house_view)
        context = prompt_context(request, profile, counterparty, evidence)
        plan = await journal.generate(
            "plan",
            PLAN_SYSTEM,
            json.dumps(
                {
                    "template": template.model_dump(),
                    "context": context,
                    "allowed_subjects": sorted(FACTORS),
                    "max_tool_calls": self._config.max_tool_calls,
                },
                ensure_ascii=False,
            ),
            Plan,
        )
        journal.trace.steps[-1].output_summary = journal.summary(
            {"template": template.model_dump(), **plan.model_dump()}
        )
        current = await self._collect(journal, plan, house_view, as_of)
        evidence = sources(profile, counterparty, news, current)
        payload: dict[str, object] = {
            "plan": plan.model_dump(),
            "context": prompt_context(request, profile, counterparty, evidence),
        }
        draft = await journal.generate(
            "draft", DRAFT_SYSTEM, json.dumps(payload, ensure_ascii=False), Draft
        )
        card = await self._reviewed(journal, DRAFT_SYSTEM, payload, draft, evidence, current, news)
        return InterpretResponse(silent=False, cards=[card])

    async def _followup(
        self, request: InterpretRequest, action: FollowupContext, journal: Journal
    ) -> InterpretResponse:
        original = await journal.tool(
            "trace.find_by_card",
            "trace of the questioned card",
            self._traces.find_by_card(
                user_id=request.user_id, client_id=request.client_id, card_id=action.card_id
            ),
        )
        journal.trace.steps[-1].output_summary = original.id
        card = original_card(original, action.card_id)
        profile = await journal.tool(
            "profile.get_profile",
            "authorized client features",
            self._profiles.get_profile(request.user_id, request.client_id),
        )
        as_of = journal.trace.created_at.date()
        cited: dict[str, HouseViewClaim] = {}
        for claim_id in cited_house_view(card):
            batch = await journal.tool(
                "house_view.chain", claim_id, self._house_view.chain(claim_id=claim_id)
            )
            cited.update({claim.id: claim for claim in current_claims(batch, as_of)})
        house_view = [cited[key] for key in sorted(cited)]
        template = {"focus": self._config.followup_focus}
        plan = await journal.generate(
            "plan",
            FOLLOWUP_PLAN_SYSTEM,
            json.dumps(
                {
                    "template": template,
                    **followup_payload(request, original, action, card, profile, house_view),
                    "allowed_subjects": sorted(FACTORS),
                    "max_tool_calls": self._config.max_tool_calls,
                },
                ensure_ascii=False,
            ),
            Plan,
        )
        journal.trace.steps[-1].output_summary = journal.summary(
            {"template": template, **plan.model_dump()}
        )
        current = await self._collect(journal, plan, house_view, as_of)
        payload: dict[str, object] = {
            "plan": plan.model_dump(),
            **followup_payload(request, original, action, card, profile, current),
        }
        draft = await journal.generate(
            "draft", FOLLOWUP_DRAFT_SYSTEM, json.dumps(payload, ensure_ascii=False), Draft
        )
        answer = await self._reviewed(
            journal,
            FOLLOWUP_DRAFT_SYSTEM,
            payload,
            draft,
            followup_evidence(card, profile, current),
            current,
            trace_news(card),
        )
        return InterpretResponse(silent=False, cards=[answer])

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
                batch = [claim for claim in batch if claim.subject == call.argument]
            else:
                batch = await journal.tool(
                    call.tool, call.argument, self._house_view.chain(claim_id=call.argument)
                )
            for claim in current_claims(batch, as_of):
                collected[claim.id] = claim
        return [collected[key] for key in sorted(collected)]

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
        card = build_card(draft, evidence, card_id=str(uuid4()), trace_id=journal.trace.id)
        round_number = 1
        try:
            verdicts = await journal.review(round_number, self._critic, card, house_view, news)
            if not verdicts:
                return card
            round_number = 2
            redraft = await journal.generate(
                "redraft",
                system,
                json.dumps(
                    {**payload, "previous_draft": draft.model_dump(), "critic_verdicts": verdicts},
                    ensure_ascii=False,
                ),
                Draft,
            )
            card = build_card(redraft, evidence, card_id=card.id, trace_id=journal.trace.id)
            verdicts = await journal.review(round_number, self._critic, card, house_view, news)
        except (DomainError, ValidationError) as error:
            journal.trace.critic_verdicts.append(f"{round_number}: error: {type(error).__name__}")
            return card.model_copy(update={"needs_review": True})
        return card.model_copy(update={"needs_review": bool(verdicts)})
