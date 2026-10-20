from shared.contracts.schemas import InterpretRequest, InterpretResponse


class Agent:
    async def interpret(self, request: InterpretRequest) -> InterpretResponse:
        raise NotImplementedError("AH-18")
