from fastapi import Request

from shared.di.container import Container


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container.request_scope()
