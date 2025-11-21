"""
HTTP Header Parser for HTTPProxy.

This module contains the HTTPHeader class for parsing, manipulating, and generating HTTP headers.
"""

from typing import Dict, Optional, Tuple


class HTTPHeader:
    """
    Parse and manipulate HTTP request/response headers.
    
    Attributes:
        method: HTTP method (GET, POST, etc.) - for requests
        path: Request path/URI - for requests
        version: HTTP version (e.g., "HTTP/1.1")
        status_code: HTTP status code - for responses
        status_message: HTTP status message - for responses
        headers: Dictionary of header fields
        body: Optional message body
    """
    
    def __init__(self, header_string: str):
        """
        Initialize HTTPHeader by parsing a raw HTTP header string.
        
        Args:
            header_string: Raw HTTP header string to parse
        """
        self.method: Optional[str] = None
        self.path: Optional[str] = None
        self.version: str = "HTTP/1.1"
        self.status_code: Optional[int] = None
        self.status_message: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.body: Optional[str] = None
        self.is_request: bool = True
        
        self._parse(header_string)
    
    def _parse(self, header_string: str) -> None:
        """
        Parse the HTTP header string and populate object attributes.
        Supports CRLF (\\r\\n), LF (\\n), and CR (\\r) line endings.
        
        Args:
            header_string: Raw HTTP header string
        """
        if not header_string:
            return
        
        # Normalize line endings: replace CRLF and CR with LF, then split
        normalized = header_string.replace('\r\n', '\n').replace('\r', '\n')
        lines = normalized.split('\n')
        
        if not lines:
            return
        
        # Parse the first line (request line or status line)
        first_line = lines[0].strip()
        if first_line.startswith('HTTP/'):
            # Response: HTTP/1.1 200 OK
            self._parse_status_line(first_line)
            self.is_request = False
        else:
            # Request: GET /path HTTP/1.1
            self._parse_request_line(first_line)
            self.is_request = True
        
        # Parse headers
        i = 1
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                # Empty line indicates end of headers
                # Everything after is the body
                if i + 1 < len(lines):
                    self.body = '\n'.join(lines[i + 1:])
                break
            
            # Parse header field
            if ':' in line:
                key, value = line.split(':', 1)
                self.headers[key.strip()] = value.strip()
            
            i += 1
    
    def _parse_request_line(self, line: str) -> None:
        """
        Parse HTTP request line (e.g., "GET /index.html HTTP/1.1").
        
        Args:
            line: Request line string
        """
        parts = line.split()
        if len(parts) >= 1:
            self.method = parts[0]
        if len(parts) >= 2:
            self.path = parts[1]
        if len(parts) >= 3:
            self.version = parts[2]
    
    def _parse_status_line(self, line: str) -> None:
        """
        Parse HTTP status line (e.g., "HTTP/1.1 200 OK").
        
        Args:
            line: Status line string
        """
        parts = line.split(None, 2)
        if len(parts) >= 1:
            self.version = parts[0]
        if len(parts) >= 2:
            try:
                self.status_code = int(parts[1])
            except ValueError:
                self.status_code = None
        if len(parts) >= 3:
            self.status_message = parts[2]
    
    # Getters
    def get_method(self) -> Optional[str]:
        """Get the HTTP method."""
        return self.method
    
    def get_path(self) -> Optional[str]:
        """Get the request path."""
        return self.path
    
    def get_version(self) -> str:
        """Get the HTTP version."""
        return self.version
    
    def get_status_code(self) -> Optional[int]:
        """Get the HTTP status code."""
        return self.status_code
    
    def get_status_message(self) -> Optional[str]:
        """Get the HTTP status message."""
        return self.status_message
    
    def get_header(self, key: str) -> Optional[str]:
        """
        Get a specific header value.
        
        Args:
            key: Header field name
        
        Returns:
            Header value or None if not found
        """
        return self.headers.get(key)
    
    def get_all_headers(self) -> Dict[str, str]:
        """Get all headers as a dictionary."""
        return self.headers.copy()
    
    def get_body(self) -> Optional[str]:
        """Get the message body."""
        return self.body
    
    # Setters
    def set_method(self, method: str) -> None:
        """Set the HTTP method."""
        self.method = method
        self.is_request = True
    
    def set_path(self, path: str) -> None:
        """Set the request path."""
        self.path = path
    
    def set_version(self, version: str) -> None:
        """Set the HTTP version."""
        self.version = version
    
    def set_status_code(self, code: int) -> None:
        """Set the HTTP status code."""
        self.status_code = code
        self.is_request = False
    
    def set_status_message(self, message: str) -> None:
        """Set the HTTP status message."""
        self.status_message = message
    
    def set_header(self, key: str, value: str) -> None:
        """
        Set or update a header field.
        
        Args:
            key: Header field name
            value: Header field value
        """
        self.headers[key] = value
    
    def add_header(self, key: str, value: str) -> None:
        """
        Add a new header field (alias for set_header).
        
        Args:
            key: Header field name
            value: Header field value
        """
        self.set_header(key, value)
    
    def remove_header(self, key: str) -> None:
        """
        Remove a header field.
        
        Args:
            key: Header field name to remove
        """
        if key in self.headers:
            del self.headers[key]
    
    def set_body(self, body: str) -> None:
        """Set the message body."""
        self.body = body
    
    def generate_header(self) -> str:
        """
        Generate a complete HTTP header string from the current state.
        
        Returns:
            Formatted HTTP header string
        """
        lines = []
        
        # Generate first line
        if self.is_request:
            # Request line: METHOD PATH VERSION
            method = self.method or "GET"
            path = self.path or "/"
            lines.append(f"{method} {path} {self.version}")
        else:
            # Status line: VERSION STATUS_CODE STATUS_MESSAGE
            code = self.status_code or 200
            message = self.status_message or "OK"
            lines.append(f"{self.version} {code} {message}")
        
        # Add headers
        for key, value in self.headers.items():
            lines.append(f"{key}: {value}")
        
        # Add empty line to separate headers from body
        lines.append("")
        
        # Add body if present
        if self.body:
            lines.append(self.body)
        
        return '\r\n'.join(lines)
    
    def __str__(self) -> str:
        """String representation of the HTTP header."""
        return self.generate_header()
    
    def __repr__(self) -> str:
        """Debug representation of the HTTPHeader object."""
        if self.is_request:
            return f"HTTPHeader(method={self.method}, path={self.path}, version={self.version})"
        else:
            return f"HTTPHeader(status={self.status_code}, message={self.status_message}, version={self.version})"