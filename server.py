# Lab 3 Proxy Server
from pstats import SortKey
import sys
import socket
import struct
import threading

import http_parser

# Constants
DEBUG = True

MIN_PORT = 1024
MAX_PORT = 65535

# Global list of sockets for cleanup
sockets = []
sockets_lock = threading.Lock()

def main(args):
    # Ensure correct arg length
    if (len(args) != 2):
        usage(args)
        sys.exit()
    
    port = int(args[1])

    # Check for a valid port
    if port < MIN_PORT or port > MAX_PORT:
        print(f"Invalid port number: {port}")
        sys.exit()

    # Run the server
    server(port)

def server(port):
    # Create a TCP listening port
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with sockets_lock:
        sockets.append(listener)

    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    if DEBUG:
        print(f"Listening on port {port}")
        print("Press Ctrl+C to stop the server")
        
    listener.bind(('', port))
    listener.listen(5)
    
    try:
        while True:
            client_socket, client_address = listener.accept()
            if DEBUG:
                print(f"Accepted connection from {client_address}")
            thread = threading.Thread(target=worker, args=(client_socket, client_address))
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        if DEBUG:
            print("\nKeyboard interrupt received. Shutting down server...")
    finally:
        # Cleanup TODO: close everything
        listener.close()
        if DEBUG:
            print("Server stopped")

def worker(client_socket, client_address):
    packet = b""

    # first just get the header
    while packet.find(b"\r\n\r\n") == -1:
         packet += client_socket.recv(1024)

    # process header TODO: allow other line endings
    raw_header = packet.split(b"\r\n\r\n")[0]
    header = http_parser.HTTPHeader(raw_header.decode())
    data = header.generate_header()
    
    # Create TCP socket to destination server
    dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with sockets_lock:
        sockets.append(dest_socket)

    if header.get_header("Connection") == "keep-alive":
        process_connection_request(client_socket, dest_socket)
    else:
        process_non_connection_request(client_socket, dest_socket, header, packet)

    return



def process_connection_request(client_socket, dest_socket):
    pass

def process_non_connection_request(client_socket, dest_socket, header, packet):
    dest = header.get_header("Host")

    try:
        # Parse host and port (default to 80 if not specified)
        if ':' in dest:
            host, port = dest.split(':')
            port = int(port)
        else:
            host = dest
            port = 80
        
        if DEBUG:
            print(f"Connecting to {host}:{port}")
        
        dest_socket.connect((host, port))
        
        # TODO: Forward request to destination server
        dest_socket.send(packet)

        
    except Exception as e:
        if DEBUG:
            print(f"Error connecting to {dest}: {e}")
    finally:
        dest_socket.close()
        client_socket.close()

    return

def usage(name):
    print(f"Usage: {name} port")

if __name__ == "__main__":
    args = sys.argv
    main(args)
