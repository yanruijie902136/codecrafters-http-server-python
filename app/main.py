import asyncio


class HTTPClientConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def recv_request(self) -> None:
        status_line = await self._reader.readuntil(b"\r\n")
        print("status line =", status_line)
        while True:
            header = await self._reader.readuntil(b"\r\n")
            if header == b"\r\n":
                break
            print("header =", header)

    async def send_response(self) -> None:
        self._writer.write(b"HTTP/1.1 200 OK\r\n\r\n")
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
            await connection.recv_request()
            await connection.send_response()


if __name__ == "__main__":
    asyncio.run(HTTPServer().start())
