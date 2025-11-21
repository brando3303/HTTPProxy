"""
Unit tests for http_parser.py HTTPHeader class.

Tests parsing, manipulation, and generation of HTTP headers with various line endings.
"""

import unittest
from http_parser import HTTPHeader


class TestHTTPHeaderParsing(unittest.TestCase):
    """Test parsing of HTTP headers."""
    
    def test_parse_simple_request(self):
        """Test parsing a basic HTTP request."""
        header_str = "GET /index.html HTTP/1.1\r\nHost: example.com\r\n\r\n"
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_method(), "GET")
        self.assertEqual(header.get_path(), "/index.html")
        self.assertEqual(header.get_version(), "HTTP/1.1")
        self.assertEqual(header.get_header("Host"), "example.com")
        self.assertTrue(header.is_request)
    
    def test_parse_request_with_multiple_headers(self):
        """Test parsing request with multiple headers."""
        header_str = (
            "POST /api/data HTTP/1.1\r\n"
            "Host: api.example.com\r\n"
            "Content-Type: application/json\r\n"
            "Content-Length: 123\r\n"
            "User-Agent: TestClient/1.0\r\n"
            "\r\n"
        )
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_method(), "POST")
        self.assertEqual(header.get_path(), "/api/data")
        self.assertEqual(header.get_header("Host"), "api.example.com")
        self.assertEqual(header.get_header("Content-Type"), "application/json")
        self.assertEqual(header.get_header("Content-Length"), "123")
        self.assertEqual(header.get_header("User-Agent"), "TestClient/1.0")
    
    def test_parse_response(self):
        """Test parsing HTTP response."""
        header_str = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            "Content-Length: 1234\r\n"
            "\r\n"
        )
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_status_code(), 200)
        self.assertEqual(header.get_status_message(), "OK")
        self.assertEqual(header.get_version(), "HTTP/1.1")
        self.assertEqual(header.get_header("Content-Type"), "text/html")
        self.assertFalse(header.is_request)
    
    def test_parse_response_with_multiword_message(self):
        """Test parsing response with multi-word status message."""
        header_str = "HTTP/1.1 404 Not Found\r\n\r\n"
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_status_code(), 404)
        self.assertEqual(header.get_status_message(), "Not Found")
    
    def test_parse_with_body(self):
        """Test parsing HTTP message with body."""
        header_str = (
            "POST /submit HTTP/1.1\r\n"
            "Host: example.com\r\n"
            "Content-Length: 13\r\n"
            "\r\n"
            "Hello, World!"
        )
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_body(), "Hello, World!")
        self.assertEqual(header.get_method(), "POST")
    
    def test_parse_empty_string(self):
        """Test parsing empty string."""
        header = HTTPHeader("")
        
        self.assertIsNone(header.get_method())
        self.assertIsNone(header.get_path())
        self.assertEqual(len(header.get_all_headers()), 0)


class TestHTTPHeaderLineEndings(unittest.TestCase):
    """Test parsing with different line ending formats."""
    
    def test_parse_with_crlf(self):
        """Test parsing with CRLF (\\r\\n) line endings."""
        header_str = "GET /test HTTP/1.1\r\nHost: example.com\r\n\r\n"
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_method(), "GET")
        self.assertEqual(header.get_path(), "/test")
        self.assertEqual(header.get_header("Host"), "example.com")
    
    def test_parse_with_lf(self):
        """Test parsing with LF (\\n) line endings."""
        header_str = "GET /test HTTP/1.1\nHost: example.com\n\n"
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_method(), "GET")
        self.assertEqual(header.get_path(), "/test")
        self.assertEqual(header.get_header("Host"), "example.com")
    
    def test_parse_with_cr(self):
        """Test parsing with CR (\\r) line endings."""
        header_str = "GET /test HTTP/1.1\rHost: example.com\r\r"
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_method(), "GET")
        self.assertEqual(header.get_path(), "/test")
        self.assertEqual(header.get_header("Host"), "example.com")
    
    def test_parse_mixed_line_endings(self):
        """Test parsing with mixed line endings."""
        header_str = "GET /test HTTP/1.1\r\nHost: example.com\nUser-Agent: Test\r\n\r\n"
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_method(), "GET")
        self.assertEqual(header.get_header("Host"), "example.com")
        # Note: This might not work perfectly with truly mixed endings,
        # but we test the tolerance of the parser
    
    def test_parse_with_body_lf(self):
        """Test parsing body with LF line endings."""
        header_str = "POST /data HTTP/1.1\nContent-Length: 11\n\nHello\nWorld"
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_body(), "Hello\nWorld")


class TestHTTPHeaderEditing(unittest.TestCase):
    """Test editing and manipulation of HTTP headers."""
    
    def test_set_method(self):
        """Test setting HTTP method."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        header.set_method("POST")
        
        self.assertEqual(header.get_method(), "POST")
        self.assertTrue(header.is_request)
    
    def test_set_path(self):
        """Test setting request path."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        header.set_path("/new/path")
        
        self.assertEqual(header.get_path(), "/new/path")
    
    def test_set_version(self):
        """Test setting HTTP version."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        header.set_version("HTTP/2.0")
        
        self.assertEqual(header.get_version(), "HTTP/2.0")
    
    def test_add_header(self):
        """Test adding a new header."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        header.add_header("Authorization", "Bearer token123")
        
        self.assertEqual(header.get_header("Authorization"), "Bearer token123")
    
    def test_set_header_overwrite(self):
        """Test overwriting an existing header."""
        header = HTTPHeader("GET / HTTP/1.1\r\nHost: old.com\r\n\r\n")
        header.set_header("Host", "new.com")
        
        self.assertEqual(header.get_header("Host"), "new.com")
    
    def test_remove_header(self):
        """Test removing a header."""
        header = HTTPHeader("GET / HTTP/1.1\r\nHost: example.com\r\nUser-Agent: Test\r\n\r\n")
        header.remove_header("User-Agent")
        
        self.assertIsNone(header.get_header("User-Agent"))
        self.assertIsNotNone(header.get_header("Host"))
    
    def test_set_body(self):
        """Test setting message body."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        header.set_body("New body content")
        
        self.assertEqual(header.get_body(), "New body content")
    
    def test_set_status_code(self):
        """Test setting status code for response."""
        header = HTTPHeader("HTTP/1.1 200 OK\r\n\r\n")
        header.set_status_code(404)
        
        self.assertEqual(header.get_status_code(), 404)
        self.assertFalse(header.is_request)
    
    def test_set_status_message(self):
        """Test setting status message."""
        header = HTTPHeader("HTTP/1.1 200 OK\r\n\r\n")
        header.set_status_message("Not Found")
        
        self.assertEqual(header.get_status_message(), "Not Found")
    
    def test_multiple_edits(self):
        """Test multiple edits in sequence."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        
        header.set_path("/api/users")
        header.set_method("POST")
        header.add_header("Content-Type", "application/json")
        header.add_header("Authorization", "Bearer xyz")
        header.set_body('{"name": "John"}')
        
        self.assertEqual(header.get_method(), "POST")
        self.assertEqual(header.get_path(), "/api/users")
        self.assertEqual(header.get_header("Content-Type"), "application/json")
        self.assertEqual(header.get_header("Authorization"), "Bearer xyz")
        self.assertEqual(header.get_body(), '{"name": "John"}')


class TestHTTPHeaderGeneration(unittest.TestCase):
    """Test generation of HTTP header strings."""
    
    def test_generate_simple_request(self):
        """Test generating a simple request header."""
        header = HTTPHeader("GET /test HTTP/1.1\r\nHost: example.com\r\n\r\n")
        generated = header.generate_header()
        
        self.assertIn("GET /test HTTP/1.1", generated)
        self.assertIn("Host: example.com", generated)
        self.assertTrue(generated.endswith("\r\n"))
    
    def test_generate_after_edit(self):
        """Test generating header after editing."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        header.set_path("/new/path")
        header.add_header("Host", "example.com")
        header.add_header("User-Agent", "TestBot/1.0")
        
        generated = header.generate_header()
        
        self.assertIn("GET /new/path HTTP/1.1", generated)
        self.assertIn("Host: example.com", generated)
        self.assertIn("User-Agent: TestBot/1.0", generated)
    
    def test_generate_response(self):
        """Test generating response header."""
        header = HTTPHeader("HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n")
        generated = header.generate_header()
        
        self.assertIn("HTTP/1.1 404 Not Found", generated)
        self.assertIn("Content-Type: text/html", generated)
    
    def test_generate_with_body(self):
        """Test generating header with body."""
        header = HTTPHeader("POST / HTTP/1.1\r\n\r\nTest Body")
        generated = header.generate_header()
        
        self.assertIn("POST / HTTP/1.1", generated)
        self.assertIn("Test Body", generated)
        # Ensure body is separated by blank line
        self.assertIn("\r\n\r\n", generated)
    
    def test_roundtrip_request(self):
        """Test parsing and regenerating maintains structure."""
        original = (
            "POST /api/data HTTP/1.1\r\n"
            "Host: api.example.com\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
        )
        header = HTTPHeader(original)
        generated = header.generate_header()
        
        # Parse the generated header
        header2 = HTTPHeader(generated)
        
        self.assertEqual(header.get_method(), header2.get_method())
        self.assertEqual(header.get_path(), header2.get_path())
        self.assertEqual(header.get_version(), header2.get_version())
        self.assertEqual(header.get_header("Host"), header2.get_header("Host"))
        self.assertEqual(header.get_header("Content-Type"), header2.get_header("Content-Type"))
    
    def test_str_method(self):
        """Test __str__ method returns same as generate_header."""
        header = HTTPHeader("GET / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        
        self.assertEqual(str(header), header.generate_header())
    
    def test_generate_preserves_all_headers(self):
        """Test that all headers are preserved in generation."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        header.add_header("Header1", "Value1")
        header.add_header("Header2", "Value2")
        header.add_header("Header3", "Value3")
        
        generated = header.generate_header()
        
        self.assertIn("Header1: Value1", generated)
        self.assertIn("Header2: Value2", generated)
        self.assertIn("Header3: Value3", generated)


class TestHTTPHeaderEdgeCases(unittest.TestCase):
    """Test edge cases and special scenarios."""
    
    def test_header_with_colon_in_value(self):
        """Test header value containing colons."""
        header_str = "GET / HTTP/1.1\r\nX-Custom: value:with:colons\r\n\r\n"
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_header("X-Custom"), "value:with:colons")
    
    def test_header_with_spaces_in_value(self):
        """Test header value with spaces."""
        header_str = "GET / HTTP/1.1\r\nUser-Agent: Mozilla/5.0 (Windows NT 10.0)\r\n\r\n"
        header = HTTPHeader(header_str)
        
        self.assertEqual(header.get_header("User-Agent"), "Mozilla/5.0 (Windows NT 10.0)")
    
    def test_path_with_query_string(self):
        """Test path with query parameters."""
        header = HTTPHeader("GET /search?q=test&page=1 HTTP/1.1\r\n\r\n")
        
        self.assertEqual(header.get_path(), "/search?q=test&page=1")
    
    def test_path_with_fragment(self):
        """Test path with fragment identifier."""
        header = HTTPHeader("GET /page#section HTTP/1.1\r\n\r\n")
        
        self.assertEqual(header.get_path(), "/page#section")
    
    def test_get_nonexistent_header(self):
        """Test getting a header that doesn't exist."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        
        self.assertIsNone(header.get_header("NonExistent"))
    
    def test_remove_nonexistent_header(self):
        """Test removing a header that doesn't exist (should not error)."""
        header = HTTPHeader("GET / HTTP/1.1\r\n\r\n")
        header.remove_header("NonExistent")  # Should not raise exception
        
        self.assertIsNone(header.get_header("NonExistent"))
    
    def test_repr_request(self):
        """Test __repr__ for request."""
        header = HTTPHeader("GET /test HTTP/1.1\r\n\r\n")
        repr_str = repr(header)
        
        self.assertIn("GET", repr_str)
        self.assertIn("/test", repr_str)
        self.assertIn("HTTP/1.1", repr_str)
    
    def test_repr_response(self):
        """Test __repr__ for response."""
        header = HTTPHeader("HTTP/1.1 200 OK\r\n\r\n")
        repr_str = repr(header)
        
        self.assertIn("200", repr_str)
        self.assertIn("OK", repr_str)


if __name__ == '__main__':
    unittest.main()
