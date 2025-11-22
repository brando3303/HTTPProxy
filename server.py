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

BUF_SIZE = 1024

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
    try :
        packet_buf = b""

        # first just get the header
        while packet_buf.find(b"\r\n\r\n") == -1:
            packet_buf += client_socket.recv(BUF_SIZE)

        # process header TODO: allow other line endings
        raw_header = packet_buf.split(b"\r\n\r\n")[0]
        packet_buf = packet_buf.split(b"\r\n\r\n",1)[1]
        header = http_parser.HTTPHeader(raw_header.decode())
        header.set_header("Connection", "close")
        header.set_version("HTTP/1.0")
        
        # Create TCP socket to destination server
        dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with sockets_lock:
            sockets.append(dest_socket)

        if header.get_method() == "CONNECT":
            pass
            #process_connection_request(client_socket, dest_socket, header, packet_buf)
        else:
            process_non_connection_request(client_socket, dest_socket, header, packet_buf)

        return
    except KeyboardInterrupt:
        if DEBUG:
            print("\nKeyboard interrupt received. Stopping worker...")
        return



def process_connection_request(client_socket, dest_socket, header, packet_buf):
    dest  = header.get_header("Host")
    print(header.generate_header())

    try:
        if ':' in dest:
            host, port = dest.split(':')
            port = int(port)
        else:
            host = dest
            port = 80
        
        if DEBUG:
            print(f"Connecting to {host}:{port}")
        
        dest_socket.connect((host, port))
        dest_socket.settimeout(5)
        client_socket.settimeout(5)

        #send what we have so far, continue sending rest of packet if any
        dest_socket.send(header.generate_header().encode() + packet_buf)
        while True:
            data = client_socket.recv(BUF_SIZE)
            if not data:
                break
            dest_socket.send(data)
        
        # Now receive response from destination and send back to client
        while True:
            response = dest_socket.recv(BUF_SIZE)
            if not response:
                break
            client_socket.send(response)
        

    except Exception as e:
        if DEBUG:
            print(f"Error connecting to {dest}: {e}")
    finally:
        dest_socket.close()
        client_socket.close()

    return

def process_non_connection_request(client_socket, dest_socket, header, packet_buf):
    dest = header.get_header("Host")
    print(header.generate_header())

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
        dest_socket.settimeout(5)
        client_socket.settimeout(5)
        
        # TODO: Forward request to destination server

        #send what we have so far, continue sending rest of packet if any
        dest_socket.send(header.generate_header().encode() + packet_buf)
        print(f"sending header to dest {repr(header.generate_header().encode())}, packet_buf length {len(packet_buf)}")
        if header.get_header("Content-Length") or header.get_header("Transfer-Encoding"):
            client_payload = b""
            while client_payload.find(b"\r\n\r\n") == -1:
                print("getting payload from client")
                try:
                    data = client_socket.recv(BUF_SIZE)
                except socket.timeout:
                    break
                if not data:
                    break
                print(f"received data of length {len(data)}")
                dest_socket.send(data)
        
        # Now receive response from destination and send back to client
        resp_buf = b""
        while resp_buf.find(b"\r\n\r\n") == -1:
            print("getting header from dest")
            try:
                response = dest_socket.recv(BUF_SIZE)
            except socket.timeout:
                print("timeout")
                break
            if not response:
                print("no response")
                break
            print(f"received data of length {len(response)}")
            resp_buf += response
        
        # process client header
        raw_header = resp_buf.split(b"\r\n\r\n")[0]
        resp_buf = resp_buf.split(b"\r\n\r\n",1)[1]
        resp_header = http_parser.HTTPHeader(raw_header.decode())
        resp_header.set_version("HTTP/1.0")
        print(f"sending header to client {resp_header.generate_header()}")

        # send header + initial recieved payload to client
        client_socket.send(resp_header.generate_header().encode())
        client_socket.send(resp_buf)
        print(f"sending payload to client {len(resp_buf)} bytes out of {content_length if content_length else 'unknown'}")

        # continue sending rest of payload if any
        content_length = resp_header.get_header("Content-Length")
        if content_length and len(resp_buf) < int(content_length) or resp_header.get_header("Transfer-Encoding"):
            while True:
                print("getting payload from dest")
                try:
                    response = dest_socket.recv(BUF_SIZE)
                except socket.timeout:
                    break
                if not response:
                    break
                print(f"received data of length {len(response)}")
                client_socket.send(response)
        print("finished sending to client")



        
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
