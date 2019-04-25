import collections.abc
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
from .connection import HTTPConnection
from .exceptions import PoolTimeout
from .models import Client, Origin, Request, Response
from .streams import PoolSemaphore

CONNECTIONS_DICT = typing.Dict[Origin, typing.List[HTTPConnection]]


class ConnectionStore(collections.abc.Sequence):
    """
    We need to maintain collections of connections in a way that allows us to:

    * Lookup connections by origin.
    * Iterate over connections by insertion time.
    * Return the total number of connections.
    """

    def __init__(self) -> None:
        self.all = {}  # type: typing.Dict[HTTPConnection, float]
        self.by_origin = (
            {}
        )  # type: typing.Dict[Origin, typing.Dict[HTTPConnection, float]]

    def pop_by_origin(self, origin: Origin) -> typing.Optional[HTTPConnection]:
        try:
            connections = self.by_origin[origin]
        except KeyError:
            return None

        connection = next(reversed(list(connections.keys())))
        del connections[connection]
        if not connections:
            del self.by_origin[origin]
        del self.all[connection]

        return connection

    def add(self, connection: HTTPConnection) -> None:
        self.all[connection] = 0.0
        try:
            self.by_origin[connection.origin][connection] = 0.0
        except KeyError:
            self.by_origin[connection.origin] = {connection: 0.0}

    def remove(self, connection: HTTPConnection) -> None:
        del self.all[connection]
        del self.by_origin[connection.origin][connection]
        if not self.by_origin[connection.origin]:
            del self.by_origin[connection.origin]

    def clear(self) -> None:
        self.all.clear()
        self.by_origin.clear()

    def __iter__(self) -> typing.Iterator[HTTPConnection]:
        return iter(self.all.keys())

    def __getitem__(self, key: typing.Any) -> typing.Any:
        if key in self.all:
            return key
        return None

    def __len__(self) -> int:
        return len(self.all)


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

        self.max_connections = PoolSemaphore(limits, timeout)
        self.keepalive_connections = ConnectionStore()
        self.active_connections = ConnectionStore()

    @property
    def num_connections(self) -> int:
        return len(self.keepalive_connections) + len(self.active_connections)

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

    async def acquire_connection(
        self, origin: Origin, timeout: typing.Optional[TimeoutConfig] = None
    ) -> HTTPConnection:
        connection = self.keepalive_connections.pop_by_origin(origin)

        if connection is None:
            await self.max_connections.acquire(timeout)
            connection = HTTPConnection(
                origin,
                ssl=self.ssl,
                timeout=self.timeout,
                pool_release_func=self.release_connection,
            )

        self.active_connections.add(connection)

        return connection

    async def release_connection(self, connection: HTTPConnection) -> None:
        if connection.is_closed:
            self.active_connections.remove(connection)
            self.max_connections.release()
        elif (
            self.limits.soft_limit is not None
            and self.num_connections > self.limits.soft_limit
        ):
            self.active_connections.remove(connection)
            self.max_connections.release()
            await connection.close()
        else:
            self.active_connections.remove(connection)
            self.keepalive_connections.add(connection)

    async def close(self) -> None:
        self.is_closed = True
        connections = list(self.keepalive_connections)
        self.keepalive_connections.clear()
        for connection in connections:
            await connection.close()
