"""Content sanitization utilities for XSS prevention."""
from bs4 import BeautifulSoup
import html
from urllib.parse import urlparse
from typing import Any

class ContentSanitizer:
    """Sanitize user-generated content to prevent XSS attacks."""

    # Allowed HTML tags and attributes
    ALLOWED_TAGS = {
        'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li',
        'blockquote', 'hr',
        'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'div', 'span', 'mark', 'sub', 'sup',
    }

    ALLOWED_ATTRIBUTES = {
        'a': {'href', 'title', 'rel', 'target'},
        'img': {'src', 'alt', 'title', 'width', 'height'},
        'td': {'colspan', 'rowspan', 'style'},
        'th': {'colspan', 'rowspan', 'style'},
        'div': {'class', 'data-*'},
        'span': {'class', 'data-*', 'style'},
        'p': {'class', 'data-*', 'style'},
        'code': {'class'},
        'pre': {'class'},
    }

    # Allowed CSS properties
    ALLOWED_CSS_PROPERTIES = {
        'color', 'background-color', 'font-weight', 'font-style',
        'text-decoration', 'text-align', 'margin', 'padding',
        'border', 'width', 'height', 'display', 'float',
    }

    @classmethod
    def sanitize_html(cls, html: str) -> str:
        """
        Sanitize HTML content to prevent XSS attacks.

        Args:
            html: Raw HTML content

        Returns:
            Sanitized HTML string
        """
        if not html:
            return ""

        soup = BeautifulSoup(html, 'html.parser')

        # Remove all tags that aren't allowed
        for tag in soup.find_all(True):
            if tag.name not in cls.ALLOWED_TAGS:
                tag.unwrap()
            else:
                # Filter attributes
                allowed_attrs = cls.ALLOWED_ATTRIBUTES.get(tag.name, set())
                attrs_to_remove = []

                for attr_name in list(tag.attrs.keys()):
                    # Check for data-* attributes
                    if attr_name.startswith('data-'):
                        continue

                    # Check if attribute is allowed
                    if attr_name not in allowed_attrs:
                        attrs_to_remove.append(attr_name)
                        continue

                    # Validate specific attributes
                    if attr_name == 'href' and tag.name == 'a':
                        url = tag.get(attr_name, '')
                        if not cls._is_safe_url(url):
                            attrs_to_remove.append(attr_name)

                    if attr_name == 'src' and tag.name == 'img':
                        url = tag.get(attr_name, '')
                        if not cls._is_safe_url(url, allow_data=True):
                            attrs_to_remove.append(attr_name)

                    if attr_name == 'style':
                        safe_style = cls._sanitize_css(tag.get(attr_name, ''))
                        if safe_style:
                            tag[attr_name] = safe_style
                        else:
                            attrs_to_remove.append(attr_name)

                for attr in attrs_to_remove:
                    del tag[attr]

        return str(soup)

    @classmethod
    def _is_safe_url(cls, url: str, allow_data: bool = False) -> bool:
        """
        Check if URL is safe (javascript: etc. are blocked).

        Args:
            url: URL to check
            allow_data: Whether to allow data: URLs (for images)

        Returns:
            True if URL is safe, False otherwise
        """
        try:
            parsed = urlparse(url)

            # Block dangerous protocols
            dangerous_protocols = {'javascript', 'vbscript', 'file'}
            if parsed.scheme in dangerous_protocols:
                return False

            # Allow data: URLs for images only
            if parsed.scheme == 'data':
                if allow_data and url.startswith('data:image/'):
                    return True
                return False

            # Only allow http, https, mailto, and relative URLs
            if parsed.scheme not in ['', 'http', 'https', 'mailto']:
                return False

            return True
        except Exception:
            return False

    @classmethod
    def _sanitize_css(cls, css: str) -> str:
        """
        Sanitize CSS style attribute.

        Only allows safe CSS properties.
        """
        if not css:
            return ""

        safe_properties = []
        for declaration in css.split(';'):
            if ':' not in declaration:
                continue

            prop, value = declaration.split(':', 1)
            prop = prop.strip().lower()
            value = value.strip()

            # Check if property is allowed
            if prop in cls.ALLOWED_CSS_PROPERTIES:
                # Additional check for url() in CSS
                if 'url(' in value:
                    if not cls._is_safe_css_url(value):
                        continue
                safe_properties.append(f"{prop}: {value}")

        return '; '.join(safe_properties)

    @classmethod
    def _is_safe_css_url(cls, value: str) -> bool:
        """Check if CSS url() value is safe."""
        # Extract URL from url()
        import re
        match = re.search(r'url\(["\']?(.*?)["\']?\)', value)
        if match:
            url = match.group(1)
            return cls._is_safe_url(url, allow_data=True)
        return True

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitize plain text (escape HTML).

        Args:
            text: Plain text input

        Returns:
            HTML-escaped text
        """
        return html.escape(text)

    @classmethod
    def sanitize_json(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Sanitize JSON data (string values only).

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = cls.sanitize_text(value)
            elif isinstance(value, dict):
                result[key] = cls.sanitize_json(value)
            elif isinstance(value, list):
                result[key] = [
                    cls.sanitize_text(item) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    @classmethod
    def sanitize_markdown(cls, markdown: str) -> str:
        """
        Sanitize markdown input by escaping HTML first.

        Args:
            markdown: Markdown input

        Returns:
            Sanitized markdown
        """
        if not markdown:
            return ""

        # Escape any HTML tags in the markdown
        # This is a simple implementation - production should use a proper markdown sanitizer
        soup = BeautifulSoup(markdown, 'html.parser')

        # Remove all HTML tags
        for tag in soup.find_all(True):
            tag.unwrap()

        return str(soup)


def sanitize_content(content: str, content_type: str = "html") -> str:
    """
    Convenience function to sanitize content based on type.

    Args:
        content: Raw content
        content_type: Type of content (html, text, markdown, json)

    Returns:
        Sanitized content
    """
    sanitizer = ContentSanitizer()

    if content_type == "html":
        return sanitizer.sanitize_html(content)
    elif content_type == "text":
        return sanitizer.sanitize_text(content)
    elif content_type == "markdown":
        return sanitizer.sanitize_markdown(content)
    elif content_type == "json":
        # Assuming content is a JSON string
        import json
        try:
            data = json.loads(content)
            return json.dumps(sanitizer.sanitize_json(data))
        except:
            return content
    else:
        return content


__all__ = [
    "ContentSanitizer",
    "sanitize_content",
]
