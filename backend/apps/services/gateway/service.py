from time import perf_counter

from apps.services.gateway.cache import InterpretCache, cache_key, context_hash
from apps.services.gateway.calls import CallJournal, CallRecord
from shared.contracts.errors import AccessDenied
from shared.contracts.ports import HouseViewService, Interpreter, ProfileService
from shared.contracts.schemas import InterpretRequest, InterpretResponse


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

    async def _authorize(self, user_id: str, client_id: str) -> None:
        if client_id not in await self._profiles.list_clients(user_id):
            raise AccessDenied(f"User {user_id} has no access to client {client_id}")

    async def interpret(self, user_id: str, request: InterpretRequest) -> InterpretResponse:
        if request.user_id != user_id:
            raise AccessDenied(f"User {user_id} cannot interpret for {request.user_id}")
        await self._authorize(user_id, request.client_id)
        start = perf_counter()
        key = cache_key(request, await self._house_view.version())
        response = await self._cache.get(key)
        cached = response is not None
        try:
            if response is None:
                response = await self._interpreter.interpret(request)
                await self._cache.put(key, response)
        except Exception as error:
            await self._journal.record(self._call(request, start, type(error).__name__))
            raise
        trace_id = response.cards[0].trace_id if response.cards else None
        await self._journal.record(self._call(request, start, "ok", cached, trace_id))
        return response.model_copy(update={"cached": cached})

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
