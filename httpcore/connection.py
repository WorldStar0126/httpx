import functools
import typing

import h2.connection
import h11

from .config import DEFAULT_SSL_CONFIG, DEFAULT_TIMEOUT_CONFIG, SSLConfig, TimeoutConfig
from .exceptions import ConnectTimeout
from .http2 import HTTP2Connection
from .http11 import HTTP11Connection
from .models import Client, Origin, Request, Response
from .streams import Protocol, connect

# Callback signature: async def callback(conn: HTTPConnection) -> None
ReleaseCallback = typing.Callable[["HTTPConnection"], typing.Awaitable[None]]


class HTTPConnection(Client):
    def __init__(
        self,
        origin: typing.Union[str, Origin],
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        release_func: typing.Optional[ReleaseCallback] = None,
    ):
        self.origin = Origin(origin) if isinstance(origin, str) else origin
        self.ssl = ssl
        self.timeout = timeout
        self.release_func = release_func
        self.h11_connection = None  # type: typing.Optional[HTTP11Connection]
        self.h2_connection = None  # type: typing.Optional[HTTP2Connection]

    async def send(
        self,
        request: Request,
        *,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> Response:
        if self.h11_connection is None and self.h2_connection is None:
            await self.connect(ssl, timeout)

        if self.h2_connection is not None:
            response = await self.h2_connection.send(request, ssl=ssl, timeout=timeout)
        else:
            assert self.h11_connection is not None
            response = await self.h11_connection.send(request, ssl=ssl, timeout=timeout)

        return response

    async def connect(
        self,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> None:
        if ssl is None:
            ssl = self.ssl
        if timeout is None:
            timeout = self.timeout

        hostname = self.origin.hostname
        port = self.origin.port
        ssl_context = await ssl.load_ssl_context() if self.origin.is_ssl else None

        if self.release_func is None:
            on_release = None
        else:
            on_release = functools.partial(self.release_func, self)

        reader, writer, protocol = await connect(hostname, port, ssl_context, timeout)
        if protocol == Protocol.HTTP_2:
            self.h2_connection = HTTP2Connection(
                reader,
                writer,
                origin=self.origin,
                timeout=self.timeout,
                on_release=on_release,
            )
        else:
            self.h11_connection = HTTP11Connection(
                reader,
                writer,
                origin=self.origin,
                timeout=self.timeout,
                on_release=on_release,
            )

    async def close(self) -> None:
        if self.h2_connection is not None:
            await self.h2_connection.close()
        elif self.h11_connection is not None:
            await self.h11_connection.close()

    @property
    def is_http2(self) -> bool:
        return self.h2_connection is not None

    @property
    def is_closed(self) -> bool:
        if self.h2_connection is not None:
            return self.h2_connection.is_closed
        else:
            assert self.h11_connection is not None
            return self.h11_connection.is_closed
