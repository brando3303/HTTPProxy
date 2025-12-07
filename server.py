# Lab 3 Proxy Server
from pstats import SortKey
import select
import sys
import socket
import struct
import threading
from typing import Tuple

import http_parser

# Constants
DEBUG = False

MIN_PORT = 1024
MAX_PORT = 65535

BUF_SIZE = 1024

# Global list of sockets for cleanup
sockets = []
sockets_lock = threading.Lock()

def add_socket(sock):
    with sockets_lock:
        sockets.append(sock)

def cleanup_socket(sock):
    with sockets_lock:
        if sock in sockets:
            sockets.remove(sock)
    sock.close()

def cleanup_all_sockets():
    with sockets_lock:
        for sock in sockets:
            sock.close()
        sockets.clear()

def main(args):
    '''
    Checks for valid arguments and begins proxy server.
    '''
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
    '''
    Handles incoming connections and spawns threads for each new one. 
    Additioanlly cleans up sockets on server close.
    Parameters:
    - port: port to run server on
    '''

    # Create a TCP listening port
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with sockets_lock:
        sockets.append(listener)

    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    print(f"Listening on port {port}")
    print("Press Ctrl+C to stop the server")
        
    listener.bind(('', port))
    listener.listen(5)
    
    try:
        while True:
            client_socket, client_address = listener.accept()
            client_socket.settimeout(5)

            if DEBUG:
                print(f"Accepted connection from {client_address}")
            thread = threading.Thread(target=worker, args=(client_socket, client_address))
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        if DEBUG:
            print("\nKeyboard interrupt received. Shutting down server...")
    finally:
        listener.close()
        cleanup_all_sockets()
        if DEBUG:
            print("Server stopped")

def worker(client_socket, client_address):
    '''
    Worker function that each thread executes
    Parameters:
    - client_socket: connection object for the client
    - client_address: client address info
    '''
    if DEBUG:
        print(f"Client address info: {client_address}")

    try :
        packet_buf = b""

        # First just get the header
        delim = b"\r\n\r\n"
        try:
            while packet_buf.find(delim) == -1 and packet_buf.find(b"\n\n") == -1:
                if packet_buf.find(b"\n\n") != -1:
                    delim = b"\n\n"
                packet_buf += client_socket.recv(BUF_SIZE)
        except TimeoutError as e:
            if DEBUG:
                print(f"Timed out: {e}")
                print(packet_buf.decode())
            
            # Cleanup socket
            cleanup_socket(client_socket)
                
            return
        except ConnectionResetError as e:
            if DEBUG:
                print(f"Connection reset: {e}")

            # Cleanup socket
            cleanup_socket(client_socket)
            return

        # Update buffer
        packet_buf = packet_buf.split(delim, 1)
        raw_header = packet_buf[0]
        if len(packet_buf) == 1:
            print(packet_buf[0])
        packet_buf = packet_buf[1]
        header = http_parser.HTTPHeader(raw_header.decode())
        header.set_header("Connection", "close")
        header.set_version("HTTP/1.0")
        if header.get_header("Proxy-Connection"):
            header.set_header("Proxy-Connection", "close")

        # Print output to console
        print(header.to_output())
        
        # Create TCP socket to destination server
        dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with sockets_lock:
            sockets.append(dest_socket)

        # Forward the request to the handler for the request type
        if header.get_method() == "CONNECT":
            process_connection_request(client_socket, dest_socket, header)
        else:
            process_non_connection_request(client_socket, dest_socket, header, packet_buf)

        return
    except KeyboardInterrupt:
        if DEBUG:
            print("\nKeyboard interrupt received. Stopping worker...")
        return

def process_connection_request(client_socket, dest_socket, header):
    '''
    Processes a connection request by creating TCP connections with
    client_socket and with dest_socket, and relays information between
    the two.
    '''
    dest = header.get_header("Host") or header.get_header("host")
    if DEBUG:
        print(header.generate_header())

    try:
        # Parse host and port (default to 80 if not specified)
        host, port = get_host_port(header)

        if DEBUG:
            print(f"Connecting to {host}:{port}")

        # We just need to connect to dest and reply ok to client
        try:
            dest_socket.connect((host, port))
            dest_socket.settimeout(5)
        except Exception as e:
            # If we cannot connect, shut down
            if DEBUG:
                print(f"Could not connect: {e}")

            error_response = "HTTP/1.0 502 Bad Gateway\r\n\r\n"
            client_socket.send(error_response.encode())
        
            cleanup_socket(dest_socket)
            cleanup_socket(client_socket)
            return

        ok_response = "HTTP/1.0 200 Connection Established\r\n\r\n"
        client_socket.send(ok_response.encode())

        # Now just forward data between client and dest
        while True:
            has_data, _, _ = select.select([client_socket, dest_socket], [], [], .0001)
            if client_socket in has_data:
                data = client_socket.recv(BUF_SIZE)
                if data == b"":
                    client_socket.close()
                    dest_socket.close()
                    break
                dest_socket.send(data)
            if dest_socket in has_data:
                data = dest_socket.recv(BUF_SIZE)
                if data == b"":
                    client_socket.close()
                    dest_socket.close()
                    break
                client_socket.send(data)

        if DEBUG:
            print("finished sending to client")

        
    except Exception as e:
        if DEBUG:
            print(f"Error connecting to {dest}: {e}")
    finally:
        cleanup_socket(dest_socket)
        cleanup_socket(client_socket)
    return

def process_non_connection_request(client_socket, dest_socket, header, packet_buf):
    '''
    Handles a non-connection request. This method sends the request from the client to
    dest_socket, and relays information back to client_socket.
    '''
    dest = header.get_header("Host") or header.get_header("host")
    if DEBUG:
        print(header.generate_header())

    try:
        # Parse host and port (default to 80 if not specified)
        host, port = get_host_port(header)
        if DEBUG:
            print(f"Connecting to {host}:{port}")
        
        dest_socket.connect((host, port))
        dest_socket.settimeout(5)
        client_socket.settimeout(5)
        
        header.change_path_to_relative()
        header.set_header("Connection", "close")
        header.set_version("HTTP/1.0")
        header.set_header("Proxy-Connection", "close")

        #send what we have so far, continue sending rest of packet if any
        dest_socket.send(header.generate_header().encode() + packet_buf)
        if DEBUG:
            print(f"sending header to dest {repr(header.generate_header().encode())}, packet_buf length {len(packet_buf)}")
        if header.get_header("Content-Length") or header.get_header("Transfer-Encoding"):
            client_payload = b""
            while client_payload.find(b"\r\n\r\n") == -1:
                if DEBUG:
                    print("getting payload from client")
                try:
                    data = client_socket.recv(BUF_SIZE)
                except socket.timeout:
                    break
                if not data:
                    break

                if DEBUG:
                    print(f"received data of length {len(data)}")
                dest_socket.send(data)
        
        # Now receive response from destination and send back to client
        resp_buf = b""
        while resp_buf.find(b"\r\n\r\n") == -1:
            if DEBUG:
                print("getting header from dest")
            try:
                response = dest_socket.recv(BUF_SIZE)
            except socket.timeout:
                if DEBUG:
                    print("timeout")
                break
            if not response:
                if DEBUG:
                    print("no response")
                break

            if DEBUG:
                print(f"received data of length {len(response)}")
            resp_buf += response
        
        # process server response header
        raw_header = resp_buf.split(b"\r\n\r\n")[0]
        resp_buf = resp_buf.split(b"\r\n\r\n",1)[1]
        resp_header = http_parser.HTTPHeader(raw_header.decode())
        resp_header.set_version("HTTP/1.0")
        resp_header.set_header("Connection", "close")
        resp_header.set_header("Proxy-Connection", "close")

        if DEBUG:
            print(f"sending header to client {resp_header.generate_header()}")

        # send header + initial recieved payload to client
        client_socket.send(resp_header.generate_header().encode())
        client_socket.send(resp_buf)

        # continue sending rest of payload if any
        content_length = resp_header.get_header("Content-Length")

        if DEBUG:
            print(f"sending payload to client {len(resp_buf)} bytes out of {content_length if content_length else 'unknown'}")
        if content_length and len(resp_buf) < int(content_length) or resp_header.get_header("Transfer-Encoding"):
            while True:
                if DEBUG:
                    print("getting payload from dest")
                try:
                    response = dest_socket.recv(BUF_SIZE)
                except socket.timeout:
                    break
                if not response:
                    break

                if DEBUG:
                    print(f"received data of length {len(response)}")
                client_socket.send(response)

        if DEBUG:
            print("finished sending to client")
    except Exception as e:
        if DEBUG:
            print(f"Error connecting to {dest}: {e}")
    finally:
        cleanup_socket(dest_socket)
        cleanup_socket(client_socket)

    return

def get_host_port(header: http_parser.HTTPHeader) -> Tuple[str, int]:
    '''
    Returns the host and port from a given HTTP request header
    '''
    dest = header.get_header("Host") or header.get_header("host")
    if ':' in dest:
        host, port = dest.split(':')
        port = int(port)
    else:
        host = dest
        port = 80

        # Set port to 443 if using HTTPS
        if ("https://" in header.get_path().lower()):
            port = 443
    return host, port

def usage(name):
    '''
    Prints out proper usage for the program
    '''
    print(f"Usage: {name} port")

if __name__ == "__main__":
    args = sys.argv
    main(args)
