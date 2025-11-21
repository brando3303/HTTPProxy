# Lab 3 Proxy Server
from pstats import SortKey
import sys
import socket
import struct
import threading

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

    listener.setsockopt(socket)

def worker():
    pass

def usage(name):
    print(f"Usage: {name} port")

if __name__ == "__main__":
    args = sys.argv
    main(args)
