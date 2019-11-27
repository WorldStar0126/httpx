import typing

from ..models import Request, Response


class BaseMiddleware:
    async def __call__(
        self, request: Request, get_response: typing.Callable
    ) -> Response:
        raise NotImplementedError  # pragma: no cover
