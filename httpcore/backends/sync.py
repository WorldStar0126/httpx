import asyncio
import typing
from types import TracebackType

from ..client import Client
from ..config import (
    DEFAULT_MAX_REDIRECTS,
    DEFAULT_POOL_LIMITS,
    DEFAULT_SSL_CONFIG,
    DEFAULT_TIMEOUT_CONFIG,
    PoolLimits,
    SSLConfig,
    TimeoutConfig,
)
from ..models import (
    URL,
    Headers,
    HeaderTypes,
    QueryParamTypes,
    Request,
    RequestData,
    Response,
    URLTypes,
)


class SyncResponse:
    def __init__(self, response: Response, loop: asyncio.AbstractEventLoop):
        self._response = response
        self._loop = loop

    @property
    def status_code(self) -> int:
        return self._response.status_code

    @property
    def reason_phrase(self) -> str:
        return self._response.reason_phrase

    @property
    def protocol(self) -> typing.Optional[str]:
        return self._response.protocol

    @property
    def headers(self) -> Headers:
        return self._response.headers

    @property
    def content(self) -> bytes:
        return self._response.content

    @property
    def text(self) -> str:
        return self._response.text

    def read(self) -> bytes:
        return self._loop.run_until_complete(self._response.read())

    def stream(self) -> typing.Iterator[bytes]:
        inner = self._response.stream()
        while True:
            try:
                yield self._loop.run_until_complete(inner.__anext__())
            except StopAsyncIteration as exc:
                break

    def raw(self) -> typing.Iterator[bytes]:
        inner = self._response.raw()
        while True:
            try:
                yield self._loop.run_until_complete(inner.__anext__())
            except StopAsyncIteration as exc:
                break

    def close(self) -> None:
        return self._loop.run_until_complete(self._response.close())

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"<{class_name}(status_code={self.status_code})>"


class SyncClient:
    def __init__(
        self,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        pool_limits: PoolLimits = DEFAULT_POOL_LIMITS,
        max_redirects: int = DEFAULT_MAX_REDIRECTS,
    ) -> None:
        self._client = Client(
            ssl=ssl,
            timeout=timeout,
            pool_limits=pool_limits,
            max_redirects=max_redirects,
        )
        self._loop = asyncio.new_event_loop()

    def request(
        self,
        method: str,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        request = Request(
            method, url, data=data, query_params=query_params, headers=headers
        )
        self.prepare_request(request)
        response = self.send(
            request,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )
        return response

    def get(
        self,
        url: URLTypes,
        *,
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "GET",
            url,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def options(
        self,
        url: URLTypes,
        *,
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "OPTIONS",
            url,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def head(
        self,
        url: URLTypes,
        *,
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = False,  #  Note: Differs to usual default.
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "HEAD",
            url,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def post(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "POST",
            url,
            data=data,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def put(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "PUT",
            url,
            data=data,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def patch(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "PATCH",
            url,
            data=data,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def delete(
        self,
        url: URLTypes,
        *,
        data: RequestData = b"",
        query_params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        return self.request(
            "DELETE",
            url,
            data=data,
            headers=headers,
            stream=stream,
            allow_redirects=allow_redirects,
            ssl=ssl,
            timeout=timeout,
        )

    def prepare_request(self, request: Request) -> None:
        self._client.prepare_request(request)

    def send(
        self,
        request: Request,
        *,
        stream: bool = False,
        allow_redirects: bool = True,
        ssl: SSLConfig = None,
        timeout: TimeoutConfig = None,
    ) -> SyncResponse:
        response = self._loop.run_until_complete(
            self._client.send(
                request,
                stream=stream,
                allow_redirects=allow_redirects,
                ssl=ssl,
                timeout=timeout,
            )
        )
        return SyncResponse(response, self._loop)

    def close(self) -> None:
        self._loop.run_until_complete(self._client.close())

    def __enter__(self) -> "SyncClient":
        return self

    def __exit__(
        self,
        exc_type: typing.Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        self.close()
