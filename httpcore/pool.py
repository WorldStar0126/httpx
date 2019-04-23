import asyncio
import typing

from .config import (
    DEFAULT_CA_BUNDLE_PATH,
    DEFAULT_POOL_LIMITS,
    DEFAULT_SSL_CONFIG,
    DEFAULT_TIMEOUT_CONFIG,
    PoolLimits,
    SSLConfig,
    TimeoutConfig,
)
from .connections import Connection
from .datastructures import Client, Origin, Request, Response
from .exceptions import PoolTimeout


class ConnectionPool(Client):
    def __init__(
        self,
        *,
        ssl: SSLConfig = DEFAULT_SSL_CONFIG,
        timeout: TimeoutConfig = DEFAULT_TIMEOUT_CONFIG,
        limits: PoolLimits = DEFAULT_POOL_LIMITS,
    ):
        self.ssl = ssl
        self.timeout = timeout
        self.limits = limits
        self.is_closed = False
        self.num_active_connections = 0
        self.num_keepalive_connections = 0
        self._keepalive_connections = (
            {}
        )  # type: typing.Dict[Origin, typing.List[Connection]]
        self._max_connections = ConnectionSemaphore(
            max_connections=self.limits.hard_limit
        )

    async def send(
        self,
        request: Request,
        *,
        ssl: typing.Optional[SSLConfig] = None,
        timeout: typing.Optional[TimeoutConfig] = None,
    ) -> Response:
        connection = await self.acquire_connection(request.url.origin, timeout=timeout)
        response = await connection.send(request, ssl=ssl, timeout=timeout)
        return response

    @property
    def num_connections(self) -> int:
        return self.num_active_connections + self.num_keepalive_connections

    async def acquire_connection(
        self, origin: Origin, timeout: typing.Optional[TimeoutConfig] = None
    ) -> Connection:
        try:
            connection = self._keepalive_connections[origin].pop()
            if not self._keepalive_connections[origin]:
                del self._keepalive_connections[origin]
            self.num_keepalive_connections -= 1
            self.num_active_connections += 1

        except (KeyError, IndexError):
            if timeout is None:
                pool_timeout = self.timeout.pool_timeout
            else:
                pool_timeout = timeout.pool_timeout

            try:
                await asyncio.wait_for(self._max_connections.acquire(), pool_timeout)
            except asyncio.TimeoutError:
                raise PoolTimeout()
            connection = Connection(
                origin,
                ssl=self.ssl,
                timeout=self.timeout,
                on_release=self.release_connection,
            )
            self.num_active_connections += 1

        return connection

    async def release_connection(self, connection: Connection) -> None:
        if connection.is_closed:
            self._max_connections.release()
            self.num_active_connections -= 1
        elif (
            self.limits.soft_limit is not None
            and self.num_connections > self.limits.soft_limit
        ):
            self._max_connections.release()
            self.num_active_connections -= 1
            await connection.close()
        else:
            self.num_active_connections -= 1
            self.num_keepalive_connections += 1
            try:
                self._keepalive_connections[connection.origin].append(connection)
            except KeyError:
                self._keepalive_connections[connection.origin] = [connection]

    async def close(self) -> None:
        self.is_closed = True


class ConnectionSemaphore:
    def __init__(self, max_connections: int = None):
        if max_connections is not None:
            self.semaphore = asyncio.BoundedSemaphore(value=max_connections)

    async def acquire(self) -> None:
        if hasattr(self, "semaphore"):
            await self.semaphore.acquire()

    def release(self) -> None:
        if hasattr(self, "semaphore"):
            self.semaphore.release()
