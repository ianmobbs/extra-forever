"""
Tests for JSONL parsing utilities.
"""

import base64

from app.utils.jsonl_parser import (
    decode_base64_body,
    extract_text_from_html,
    is_html,
    parse_iso_date,
)


class TestDecodeBase64Body:
    """Tests for base64 body decoding."""

    def test_decode_base64_body(self):
        """Test basic base64 decoding."""
        encoded = base64.b64encode(b"Hello, World!").decode("utf-8")
        result = decode_base64_body(encoded)
        assert result == "Hello, World!"

    def test_decode_base64_body_with_unicode(self):
        """Test base64 decoding with unicode characters."""
        encoded = base64.b64encode("Hello, 世界!".encode()).decode("utf-8")
        result = decode_base64_body(encoded)
        assert result == "Hello, 世界!"

    def test_decode_base64_body_with_html(self):
        """Test base64 decoding with HTML content."""
        html = "<html><body><p>Hello</p></body></html>"
        encoded = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        result = decode_base64_body(encoded)
        assert result == html


class TestIsHtml:
    """Tests for HTML detection."""

    def test_is_html_with_html_tag(self):
        """Test detection of HTML content with html tag."""
        assert is_html("<html><body>content</body></html>") is True

    def test_is_html_with_div_tag(self):
        """Test detection of HTML content with div tag."""
        assert is_html("<div>content</div>") is True

    def test_is_html_with_p_tag(self):
        """Test detection of HTML content with p tag."""
        assert is_html("<p>content</p>") is True

    def test_is_html_with_span_tag(self):
        """Test detection of HTML content with span tag."""
        assert is_html("<span>content</span>") is True

    def test_is_html_with_table_tag(self):
        """Test detection of HTML content with table tag."""
        assert is_html("<table><tr><td>data</td></tr></table>") is True

    def test_is_html_with_link_tag(self):
        """Test detection of HTML content with link tag."""
        assert is_html('<link rel="stylesheet" href="style.css">') is True

    def test_is_html_with_plain_text(self):
        """Test that plain text is not detected as HTML."""
        assert is_html("This is plain text content") is False

    def test_is_html_case_insensitive(self):
        """Test that HTML detection is case insensitive."""
        assert is_html("<HTML><BODY>content</BODY></HTML>") is True
        assert is_html("<DiV>content</DiV>") is True

    def test_is_html_with_partial_tags(self):
        """Test detection with partial HTML tags in text."""
        # Should detect HTML even if content mentions tags
        assert is_html("Use the <div> element") is True


class TestExtractTextFromHtml:
    """Tests for HTML text extraction."""

    def test_extract_text_from_simple_html(self):
        """Test extraction from simple HTML."""
        html = "<html><body><p>Hello, World!</p></body></html>"
        result = extract_text_from_html(html)
        assert result == "Hello, World!"

    def test_extract_text_from_complex_html(self):
        """Test extraction from complex HTML with multiple elements."""
        html = """
        <html>
            <head><title>Title</title></head>
            <body>
                <h1>Heading</h1>
                <p>First paragraph.</p>
                <p>Second paragraph.</p>
            </body>
        </html>
        """
        result = extract_text_from_html(html)
        # Check that all text content is present
        assert "Title" in result
        assert "Heading" in result
        assert "First paragraph" in result
        assert "Second paragraph" in result
        # Check that tags are removed
        assert "<h1>" not in result
        assert "<p>" not in result

    def test_extract_text_removes_script_tags(self):
        """Test that script tags are removed."""
        html = """
        <html>
            <body>
                <p>Visible content</p>
                <script>alert('This should not appear');</script>
            </body>
        </html>
        """
        result = extract_text_from_html(html)
        assert "Visible content" in result
        assert "alert" not in result
        assert "This should not appear" not in result

    def test_extract_text_removes_style_tags(self):
        """Test that style tags are removed."""
        html = """
        <html>
            <head>
                <style>
                    body { color: red; }
                </style>
            </head>
            <body>
                <p>Visible content</p>
            </body>
        </html>
        """
        result = extract_text_from_html(html)
        assert "Visible content" in result
        assert "color: red" not in result

    def test_extract_text_normalizes_whitespace(self):
        """Test that whitespace is normalized."""
        html = """
        <html>
            <body>
                <p>Text   with     multiple    spaces</p>
                <p>Text
                with
                newlines</p>
            </body>
        </html>
        """
        result = extract_text_from_html(html)
        # Multiple spaces should be collapsed
        assert "  " not in result
        # Should have single spaces
        assert "Text with multiple spaces" in result

    def test_extract_text_from_table(self):
        """Test extraction from HTML table."""
        html = """
        <table>
            <tr>
                <td>Cell 1</td>
                <td>Cell 2</td>
            </tr>
            <tr>
                <td>Cell 3</td>
                <td>Cell 4</td>
            </tr>
        </table>
        """
        result = extract_text_from_html(html)
        assert "Cell 1" in result
        assert "Cell 2" in result
        assert "Cell 3" in result
        assert "Cell 4" in result

    def test_extract_text_from_nested_elements(self):
        """Test extraction from deeply nested HTML."""
        html = """
        <div>
            <div>
                <span>
                    <strong>Nested text</strong>
                </span>
            </div>
        </div>
        """
        result = extract_text_from_html(html)
        assert result == "Nested text"

    def test_extract_text_strips_result(self):
        """Test that result is stripped of leading/trailing whitespace."""
        html = "   <p>Content</p>   "
        result = extract_text_from_html(html)
        assert result == "Content"
        assert result[0] != " "
        assert result[-1] != " "

    def test_extract_text_from_empty_html(self):
        """Test extraction from empty HTML."""
        html = "<html><body></body></html>"
        result = extract_text_from_html(html)
        assert result == ""


class TestParseIsoDate:
    """Tests for ISO date parsing."""

    def test_parse_iso_date_with_z_suffix(self):
        """Test parsing ISO date with Z suffix."""
        date_str = "2024-01-15T10:30:00Z"
        result = parse_iso_date(date_str)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 0

    def test_parse_iso_date_with_timezone(self):
        """Test parsing ISO date with timezone offset."""
        date_str = "2024-01-15T10:30:00+00:00"
        result = parse_iso_date(date_str)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_iso_date_with_microseconds(self):
        """Test parsing ISO date with microseconds."""
        date_str = "2024-01-15T10:30:00.123456Z"
        result = parse_iso_date(date_str)
        assert result.year == 2024
        assert result.microsecond == 123456
