# Uncomment this to pass the first stage
import socket


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    # Uncomment this to pass the first stage

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    client_socket, _ = server_socket.accept() # wait for client

    data = client_socket.recv(1024)
    request = data.decode()
    request_lines = request.split("\r\n")
    _, target, _ = request_lines[0].split()

    if target.startswith("/echo/"):
        echo_str = target[6:]
        response = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(echo_str)}\r\n\r\n{echo_str}"
    elif target == "/":
        response = "HTTP/1.1 200 OK\r\n\r\n"
    else:
        response = "HTTP/1.1 404 Not Found\r\n\r\n"
    client_socket.sendall(response.encode())


if __name__ == "__main__":
    main()
