"""
Tests for message content parsing in MessagesService.
"""

import base64

from app.services.messages_service import MessagesService


class TestParseMessageContent:
    """Tests for the parse_message_content method."""

    def test_parse_plain_text_not_encoded(self):
        """Test parsing plain text that is not base64-encoded."""
        content = "This is plain text content"
        result = MessagesService.parse_message_content(content, is_base64_encoded=False)
        assert result == content

    def test_parse_html_not_encoded(self):
        """Test parsing HTML that is not base64-encoded."""
        html_content = "<html><body><p>Hello, World!</p></body></html>"
        result = MessagesService.parse_message_content(html_content, is_base64_encoded=False)
        # HTML should be extracted to plain text
        assert result == "Hello, World!"
        assert "<html>" not in result
        assert "<p>" not in result

    def test_parse_base64_plain_text(self):
        """Test parsing base64-encoded plain text."""
        plain_text = "Hello, World!"
        encoded = base64.b64encode(plain_text.encode("utf-8")).decode("utf-8")
        result = MessagesService.parse_message_content(encoded, is_base64_encoded=True)
        assert result == plain_text

    def test_parse_base64_html(self):
        """Test parsing base64-encoded HTML."""
        html = "<html><body><h1>Title</h1><p>Content here</p></body></html>"
        encoded = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        result = MessagesService.parse_message_content(encoded, is_base64_encoded=True)
        # Should be decoded and HTML extracted
        assert "Title" in result
        assert "Content here" in result
        assert "<html>" not in result
        assert "<p>" not in result

    def test_parse_complex_html_with_script_tags(self):
        """Test parsing HTML with script tags that should be removed."""
        html = """
        <html>
            <head>
                <script>alert('hello');</script>
            </head>
            <body>
                <p>Visible content</p>
                <script>console.log('test');</script>
            </body>
        </html>
        """
        encoded = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        result = MessagesService.parse_message_content(encoded, is_base64_encoded=True)
        # Should have visible content but no scripts
        assert "Visible content" in result
        assert "alert" not in result
        assert "console.log" not in result
        assert "<script>" not in result

    def test_parse_html_with_style_tags(self):
        """Test parsing HTML with style tags that should be removed."""
        html = """
        <html>
            <head>
                <style>
                    body { color: red; }
                    p { font-size: 14px; }
                </style>
            </head>
            <body>
                <p>Content</p>
            </body>
        </html>
        """
        encoded = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        result = MessagesService.parse_message_content(encoded, is_base64_encoded=True)
        # Should have content but no styles
        assert "Content" in result
        assert "color: red" not in result
        assert "font-size" not in result

    def test_parse_html_normalizes_whitespace(self):
        """Test that HTML parsing normalizes whitespace."""
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
        encoded = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        result = MessagesService.parse_message_content(encoded, is_base64_encoded=True)
        # Should normalize whitespace
        assert "Text with multiple spaces" in result
        assert "Text with newlines" in result
        # Should not have multiple consecutive spaces
        assert "  " not in result

    def test_parse_email_with_html_table(self):
        """Test parsing an email with an HTML table."""
        html = """
        <html>
            <body>
                <p>Here's your invoice:</p>
                <table>
                    <tr><td>Item</td><td>Price</td></tr>
                    <tr><td>Widget</td><td>$10.00</td></tr>
                    <tr><td>Gadget</td><td>$20.00</td></tr>
                </table>
                <p>Total: $30.00</p>
            </body>
        </html>
        """
        encoded = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        result = MessagesService.parse_message_content(encoded, is_base64_encoded=True)
        # Should have all text content
        assert "Here's your invoice" in result
        assert "Item" in result
        assert "Price" in result
        assert "Widget" in result
        assert "$10.00" in result
        assert "Total: $30.00" in result
        # Should not have HTML tags
        assert "<table>" not in result
        assert "<tr>" not in result
        assert "<td>" not in result

    def test_parse_unicode_content(self):
        """Test parsing content with unicode characters."""
        content = "Hello, 世界! 🌍"
        encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        result = MessagesService.parse_message_content(encoded, is_base64_encoded=True)
        assert result == content

    def test_parse_empty_html(self):
        """Test parsing empty HTML."""
        html = "<html><body></body></html>"
        encoded = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        result = MessagesService.parse_message_content(encoded, is_base64_encoded=True)
        assert result == ""

    def test_parse_mixed_html_and_text(self):
        """Test parsing HTML with mixed formatting."""
        html = """
        <html>
            <body>
                <h1>Important Email</h1>
                <p>Dear Customer,</p>
                <p>Thank you for your <strong>order</strong>. Your items will ship <em>soon</em>.</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                    <li>Item 3</li>
                </ul>
                <p>Best regards,<br>Support Team</p>
            </body>
        </html>
        """
        encoded = base64.b64encode(html.encode("utf-8")).decode("utf-8")
        result = MessagesService.parse_message_content(encoded, is_base64_encoded=True)
        # Should have all text content
        assert "Important Email" in result
        assert "Dear Customer" in result
        assert "Thank you for your order" in result
        assert "ship soon" in result
        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" in result
        assert "Best regards" in result
        assert "Support Team" in result
        # Should not have HTML tags
        assert "<h1>" not in result
        assert "<strong>" not in result
        assert "<em>" not in result
        assert "<ul>" not in result
        assert "<li>" not in result
        assert "<br>" not in result
