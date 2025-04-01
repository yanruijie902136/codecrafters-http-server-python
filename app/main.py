import asyncio
import dataclasses
import typing


@dataclasses.dataclass(frozen=True)
class HTTPRequestLine:
    method: str
    target: str
    version: str

    @classmethod
    async def parse(cls, reader: asyncio.StreamReader) -> typing.Self:
        data = (await reader.readuntil(b"\r\n"))[:-2].decode()
        method, target, version = data.split(" ")
        return cls(method, target, version)


@dataclasses.dataclass(frozen=True)
class HTTPRequest:
    request_line: HTTPRequestLine
    headers: dict[str, str]

    @classmethod
    async def parse(cls, reader: asyncio.StreamReader) -> typing.Self:
        request_line = await HTTPRequestLine.parse(reader)
        headers = {}
        while True:
            data = (await reader.readuntil(b"\r\n"))[:-2].decode()
            if not data:
                return cls(request_line, headers)
            i = data.index(":")
            name, value = data[:i], data[i+1:].strip()
            headers[name] = value


@dataclasses.dataclass(frozen=True)
class HTTPStatusLine:
    status_code: int
    reason_phrase: str = ""

    def encode(self) -> bytes:
        return f"HTTP/1.1 {self.status_code} {self.reason_phrase}\r\n".encode()

    @classmethod
    def ok(cls) -> typing.Self:
        return cls(200, "OK")

    @classmethod
    def not_found(cls) -> typing.Self:
        return cls(404, "Not Found")


class Stringifiable(typing.Protocol):
    def __str__(self) -> str:
        ...


@dataclasses.dataclass(frozen=True)
class HTTPResponse:
    status_line: HTTPStatusLine
    headers: dict[str, Stringifiable] = dataclasses.field(default_factory=dict)
    body: str = ""

    def encode(self) -> bytes:
        return b"".join([
            self.status_line.encode(),
            b"".join(
                f"{name}: {value}\r\n".encode() for name, value in self.headers.items()
            ),
            b"\r\n",
            self.body.encode(),
        ])


class HTTPClientConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def recv_request(self) -> HTTPRequest:
        return await HTTPRequest.parse(self._reader)

    async def send_response(self, response: HTTPResponse) -> None:
        self._writer.write(response.encode())
        await self._writer.drain()

    async def __aenter__(self) -> None:
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._writer.close()
        await self._writer.wait_closed()


class HTTPServer:
    async def start(self) -> None:
        server = await asyncio.start_server(self._client_connected_cb, host="localhost", port=4221, reuse_port=True)
        async with server:
            await server.serve_forever()

    async def _client_connected_cb(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        connection = HTTPClientConnection(reader, writer)
        async with connection:
            request = await connection.recv_request()

            if request.request_line.target == "/user-agent":
                body = request.headers["User-Agent"]
                response = HTTPResponse(
                    status_line=HTTPStatusLine.ok(),
                    headers={
                        "Content-Type": "text/plain",
                        "Content-Length": len(body),
                    },
                    body=body,
                )
            elif request.request_line.target.startswith("/echo/"):
                body = request.request_line.target[6:]
                response = HTTPResponse(
                    status_line=HTTPStatusLine.ok(),
                    headers={
                        "Content-Type": "text/plain",
                        "Content-Length": len(body),
                    },
                    body=body,
                )
            elif request.request_line.target == "/":
                response = HTTPResponse(status_line=HTTPStatusLine.ok())
            else:
                response = HTTPResponse(status_line=HTTPStatusLine.not_found())

            await connection.send_response(response)


if __name__ == "__main__":
    asyncio.run(HTTPServer().start())
