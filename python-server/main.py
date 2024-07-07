import socket
import os
import mimetypes

def start_server(host, port):
    """
    AF_INET - IPv4
    AF_INET6 - IPv6
    AF_UNIX - Uses file system path name for communication
            between processes on the same host

    SOCK_STREAM - TCP
    SOCK_DGRAM - UDP
    SOCK_RAW - Custom Protocol
    """
    # Initialize the socket as IPv4 TCp
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    """
    SO_REUSEPORT - Allows multiple sockets on the same host to bind to
                the same port. Improving scalability and load balancing.
    SO_KEEPALIVE - Keep connections active and detects broken connections
    SO_LINGER - Makes sure all data is sent before closing the connection
    TCP_NODELAY - Reduce latency. Sends small packets fast
    """
    # set any configurations
    # in this case allow reuse of address in case of TIME_WAIT state
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # bind the socket to the host and port
    server_socket.bind((host, port))

    # 5 is the number of pending connections allowed to be queued
    server_socket.listen(5)

    print(f"Server started on {host}:{port}")

    return server_socket

def parse_request(request_data):
    lines = request_data.split('\r\n')

    request_line = lines[0] 
    # GET, /, HTTP/1.1
    method, path, http_version = request_line.split(' ')

    print(f"Method: {method}, Path: {path}, HTTP Version: {http_version}")

    headers = {}
    for line in lines[1:]:
        if line == '':
            break
        header_name, header_value = line.split(': ', 1)
        headers[header_name] = header_value

    print("Headers:")
    for header_name, header_value in headers.items():
        print(f"{header_name}: {header_value}")

    return method, path, http_version, headers

def get_content_type(file_path):
    # returns content type and encoding
    content_type, _ = mimetypes.guess_type(file_path)

    """
    - default to 'application/octet-stream' which is a binary data stream'
    - many browsers prompt the user to download the file rather than displaying it
    """
    return content_type or 'application/octet-stream'

def serve_static_file(client_socket, path):
    try:
        if os.path.exists(path):
            with open(path, 'rb') as f:
                content = f.read()
            
            headers = {
                'Content-Type': get_content_type(path),
                'Content-Length': str(len(content))
            }

            response = generate_response(200, headers, content.decode('latin-1'))
        else:
            response = generate_response(404, {}, '404 Not Found')
        client_socket.sendall(response)
    except Exception as e:
        print(f"Error serving static file: {e}")
        response = generate_response(500, {}, '500 Internal Server Error')
        client_socket.sendall(response)

def generate_response(status_code, headers, body):
    status_messages = {
        200: 'OK',
        404: 'Not Found',
        500: 'Internal Server Error'
    }

    status_message = status_messages.get(status_code, 'Unknown Status')
    response_line = f"HTTP/1.1 {status_code} {status_message}\r\n"

    header_lines = ''
    for header_name, header_value in headers.items():
        header_lines += f"{header_name}: {header_value}\r\n"

    response = response_line + header_lines + '\r\n' + body
    return response.encode('utf-8')

def handle_client(client_socket):
    try:
        request_data = client_socket.recv(1024).decode('utf-8')  # Buffer size of 1024 bytes
        method, path, http_version, headers = parse_request(request_data)

        if path == "/":
            response_body = "<html><body><h1>Hello, world!</h1></body></html>"
            headers = {
                'Content-Type': 'text/html',
                'Content-Length': str(len(response_body))
            }
            response = generate_response(200, headers, response_body)
        else:
            serve_static_file(client_socket, path.lstrip('/'))
    except Exception as e:
        print(f"Error handling client: {e}")
        response = generate_response(500, {}, '500 Internal Server Error')
        client_socket.sendall(response)
    finally:
        # Close the client connection
        client_socket.close()

if __name__ == "__main__":
    host = '127.0.0.1'
    port = 8080
    server_socket = start_server(host, port)

    try:
        while True:
            """
            - waits for a client connection request
            - when it recieves one it creates a new socket for the client
            - original server socket then continues to listen for more connections
            - also returns the client address (IP address and port #)
            """
            client_socket, client_address = server_socket.accept()
            handle_client(client_socket)
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()
        print("Server closed.")

