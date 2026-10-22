import logging
from time import perf_counter

from apps.services.gateway.cache import InterpretCache, cache_key, context_hash
from apps.services.gateway.calls import CallJournal, CallRecord
from shared.contracts.errors import AccessDenied
from shared.contracts.ports import HouseViewService, Interpreter, ProfileService
from shared.contracts.schemas import InterpretRequest, InterpretResponse

logger = logging.getLogger(__name__)


class InterpretGateway:
    def __init__(
        self,
        interpreter: Interpreter,
        house_view: HouseViewService,
        profiles: ProfileService,
        cache: InterpretCache,
        journal: CallJournal,
    ) -> None:
        self._interpreter = interpreter
        self._house_view = house_view
        self._profiles = profiles
        self._cache = cache
        self._journal = journal

    async def interpret(self, user_id: str, request: InterpretRequest) -> InterpretResponse:
        if request.user_id != user_id:
            raise AccessDenied(f"User {user_id} cannot interpret for {request.user_id}")
        profile = await self._profiles.get_profile(user_id, request.client_id)
        start = perf_counter()
        key = cache_key(request, profile.version, await self._house_view.version())
        response = await self._cache.get(key)
        cached = response is not None
        if response is None:
            try:
                response = await self._interpreter.interpret(request)
            except Exception as error:
                await self._record(self._call(request, start, type(error).__name__))
                raise
            if not _needs_review(response):
                await self._remember(key, response)
        trace_id = response.cards[0].trace_id if response.cards else None
        await self._record(self._call(request, start, "ok", cached, trace_id))
        return response.model_copy(update={"cached": cached})

    async def _remember(self, key: str, response: InterpretResponse) -> None:
        try:
            await self._cache.put(key, response)
        except Exception:
            logger.exception("Gateway cache write failed for key %s", key)

    async def _record(self, call: CallRecord) -> None:
        try:
            await self._journal.record(call)
        except Exception:
            logger.exception("Gateway call journal write failed for trace %s", call.trace_id)

    def _call(
        self,
        request: InterpretRequest,
        start: float,
        outcome: str,
        cached: bool = False,
        trace_id: str | None = None,
    ) -> CallRecord:
        return CallRecord(
            user_id=request.user_id,
            client_id=request.client_id,
            action_type=request.action_context.type,
            context_hash=context_hash(request.action_context),
            trace_id=trace_id,
            cached=cached,
            outcome=outcome,
            duration_ms=int((perf_counter() - start) * 1000),
        )


def _needs_review(response: InterpretResponse) -> bool:
    return any(card.needs_review for card in response.cards)
