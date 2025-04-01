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


class HTTPClientConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def recv_request(self) -> tuple[HTTPRequestLine, dict[str, str]]:
        request_line = await HTTPRequestLine.parse(self._reader)
        headers = {}
        while True:
            data = (await self._reader.readuntil(b"\r\n"))[:-2].decode()
            if not data:
                return request_line, headers
            i = data.index(":")
            field_name, field_value = data[:i], data[i+1:].strip()
            headers[field_name] = field_value

    async def send_response(self, response: bytes) -> None:
        self._writer.write(response)
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
            request_line, _ = await connection.recv_request()
            if request_line.target == "/":
                response = b"HTTP/1.1 200 OK\r\n\r\n"
            else:
                response = b"HTTP/1.1 404 Not Found\r\n\r\n"
            await connection.send_response(response)


if __name__ == "__main__":
    asyncio.run(HTTPServer().start())
