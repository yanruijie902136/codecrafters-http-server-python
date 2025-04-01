import argparse
import asyncio
import dataclasses
import os
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
    body: str

    @classmethod
    async def parse(cls, reader: asyncio.StreamReader) -> typing.Self:
        request_line = await HTTPRequestLine.parse(reader)

        headers = {}
        while True:
            data = (await reader.readuntil(b"\r\n"))[:-2].decode()
            if not data:
                break
            i = data.index(":")
            name, value = data[:i], data[i+1:].strip()
            headers[name] = value

        body = ""
        if (value := headers.get("Content-Length")) is not None:
            body = (await reader.readexactly(int(value))).decode()

        return cls(request_line, headers, body)


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
    def created(cls) -> typing.Self:
        return cls(201, "Created")

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
    def __init__(self, directory: str) -> None:
        self._directory = directory

    async def start(self) -> None:
        server = await asyncio.start_server(self._client_connected_cb, host="localhost", port=4221, reuse_port=True)
        async with server:
            await server.serve_forever()

    async def _client_connected_cb(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        connection = HTTPClientConnection(reader, writer)
        async with connection:
            request = await connection.recv_request()
            response = self._handle_request(request)
            await connection.send_response(response)

    def _handle_request(self, request: HTTPRequest) -> HTTPResponse:
        if request.request_line.target.startswith("/echo/"):
            return self._handle_echo_endpoint(request)
        if request.request_line.target.startswith("/files/"):
            return self._handle_files_endpoint(request)
        if request.request_line.target == "/user-agent":
            return self._handle_user_agent_endpoint(request)

        if request.request_line.target == "/":
            return HTTPResponse(status_line=HTTPStatusLine.ok())
        return HTTPResponse(status_line=HTTPStatusLine.not_found())

    def _handle_echo_endpoint(self, request: HTTPRequest) -> HTTPResponse:
        compression_schemes = request.headers.get("Accept-Encoding")
        if compression_schemes is not None:
            compression_schemes = compression_schemes.split(",")
        else:
            compression_schemes = []

        body = request.request_line.target[6:]

        headers = {
            "Content-Type": "text/plain",
            "Content-Length": len(body),
        }
        if "gzip" in compression_schemes:
            headers["Content-Encoding"] = "gzip"

        return HTTPResponse(
            status_line=HTTPStatusLine.ok(),
            headers=headers,
            body=body,
        )

    def _handle_files_endpoint(self, request: HTTPRequest) -> HTTPResponse:
        filename = request.request_line.target[7:]
        path = os.path.join(self._directory, filename)

        if request.request_line.method == "POST":
            with open(path, mode="w") as f:
                f.write(request.body)
            return HTTPResponse(status_line=HTTPStatusLine.created())

        try:
            with open(path, mode="r") as f:
                body = f.read()
        except FileNotFoundError:
            return HTTPResponse(status_line=HTTPStatusLine.not_found())

        return HTTPResponse(
            status_line=HTTPStatusLine.ok(),
            headers={
                "Content-Type": "application/octet-stream",
                "Content-Length": len(body),
            },
            body=body,
        )

    def _handle_user_agent_endpoint(self, request: HTTPRequest) -> HTTPResponse:
        body = request.headers["User-Agent"]
        return HTTPResponse(
            status_line=HTTPStatusLine.ok(),
            headers={
                "Content-Type": "text/plain",
                "Content-Length": len(body),
            },
            body=body,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CodeCrafters - Build your own HTTP server")
    parser.add_argument("--directory", type=str, default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = HTTPServer(directory=args.directory)
    asyncio.run(server.start())


if __name__ == "__main__":
    main()
