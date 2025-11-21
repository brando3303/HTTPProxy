# Lab 3 Proxy Server
import sys
import socket
import struct
import threading

# Constants
DEBUG = True

# Global list of sockets for cleanup
sockets = []
sockets_lock = threading.Lock()

def main(args):
    # Ensure correct arg length
    if (len(args) != 2):
        Usage(args)
    
    port = int(args[1])

    

def server(args):
    

def usage(name):
    print(f"Usage: {name} port")

if __name__ == "__main__":
    args = sys.argv
    main(args)
