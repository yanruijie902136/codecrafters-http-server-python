#!/usr/bin/env python3
# coding=utf-8

import os
import select
import socket
import sys


rootDirectory = ""


class HttpRequest:
    def __init__(self):
        self.__method = ""
        self.__target = ""
        self.__version = ""
        self.__headers = {}
        self.__body = ""

    @staticmethod
    def recvFromSocket(sock: socket.socket):
        requestLines = sock.recv(1024).decode().split("\r\n")

        request = HttpRequest()
        request.__method, request.__target, request.__version = requestLines[0].split()
        request.__body = requestLines[-1]
        for headerLine in requestLines[1:]:
            if not headerLine:
                break
            field, value = headerLine.split(":", maxsplit=1)
            request.__headers[field] = value.lstrip().rstrip()

        return request

    @property
    def method(self):
        return self.__method

    @property
    def target(self):
        return self.__target

    @property
    def version(self):
        return self.__version

    @property
    def headers(self):
        return self.__headers

    @property
    def body(self):
        return self.__body

    def __str__(self):
        return (
            f"{self.__method} {self.__target} {self.__version}\r\n" +
            "".join([f"{key}: {value}\r\n" for key, value in self.__headers.items()]) +
            "\r\n" +
            self.__body
        )


class HttpResponse:
    def __init__(self):
        self.__version = ""
        self.__status = ""
        self.__headers = {}
        self.__body = ""

    def sendToSocket(self, sock: socket.socket):
        sock.sendall(str(self).encode())

    @staticmethod
    def handleRequest(request: HttpRequest):
        response = HttpResponse()
        response.__version = request.version

        if request.target == "/user-agent":
            response.__handleUserAgent(request)
        elif request.target.startswith("/echo/"):
            response.__handleEcho(request)
        elif request.target.startswith("/files/"):
            response.__handleFiles(request)
        else:
            response.__handleUrlPath(request)

        return response

    def __handleEcho(self, request: HttpRequest):
        self.__status = "200 OK"
        self.__body = request.target[6:]
        self.__headers["Content-Type"] = "text/plain"
        self.__headers["Content-Length"] = len(self.__body)

    def __handleFiles(self, request: HttpRequest):
        try:
            filePath = request.target[7:]
            with open(f"{rootDirectory}/{filePath}", "r") as fp:
                self.__body = fp.read()
            self.__status = "200 OK"
            self.__headers["Content-Type"] = "application/octet-stream"
            self.__headers["Content-Length"] = len(self.__body)
        except IOError:
            self.__status = "404 Not Found"
            return

    def __handleUrlPath(self, request: HttpRequest):
        self.__status = "200 OK" if request.target == "/" else "404 Not Found"

    def __handleUserAgent(self, request: HttpRequest):
        self.__status = "200 OK"
        self.__body = request.headers["User-Agent"]
        self.__headers["Content-Type"] = "text/plain"
        self.__headers["Content-Length"] = len(self.__body)

    def __str__(self):
        return (
            f"{self.__version} {self.__status}\r\n" +
            "".join([f"{key}: {value}\r\n" for key, value in self.__headers.items()]) +
            "\r\n" +
            self.__body
        )


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    if len(sys.argv) < 3:
        print("Usage: ./your_program.sh --directory <rootDirectory>", file=sys.stderr)
        exit(1)
    rootDirectory = sys.argv[2]

    serverSocket = socket.create_server(("localhost", 4221), reuse_port=True)
    activeSockets = set([serverSocket])
    while True:
        readSockets, *_ = select.select(activeSockets, [], [])

        for readSocket in readSockets:
            if readSocket == serverSocket:
                clientSocket, _ = serverSocket.accept()
                activeSockets.add(clientSocket)
            else:
                request = HttpRequest.recvFromSocket(readSocket)
                print(request)
                response = HttpResponse.handleRequest(request)
                print(response)
                response.sendToSocket(readSocket)

                readSocket.close()
                activeSockets.remove(readSocket)


if __name__ == "__main__":
    main()
