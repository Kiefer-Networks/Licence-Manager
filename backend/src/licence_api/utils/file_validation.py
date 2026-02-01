"""File validation utilities for secure file uploads."""

import re

def _decode_xml_entities(content: bytes) -> bytes:
    """Decode XML/HTML numeric entities in content.

    Decodes &#xNN; (hex) and &#NNN; (decimal) entities to their
    character equivalents for security checking.

    Args:
        content: Content with potential XML entities

    Returns:
        Content with entities decoded
    """
    def replace_entity(match: re.Match) -> bytes:
        entity = match.group(0).decode('ascii')
        if entity.startswith('&#x'):
            # Hex entity: &#x41; -> 'A'
            char_code = int(entity[3:-1], 16)
        else:
            # Decimal entity: &#65; -> 'A'
            char_code = int(entity[2:-1])
        # Only decode ASCII range for security check
        if 0 <= char_code < 128:
            return bytes([char_code])
        return match.group(0)

    return re.sub(rb'&#x?[0-9a-fA-F]+;', replace_entity, content)


def _contains_dangerous_content(content: bytes) -> bool:
    """Check if decoded content contains dangerous SVG patterns.

    Args:
        content: Decoded content to check

    Returns:
        True if dangerous content is found
    """
    content_lower = content.lower()

    # Check for dangerous elements
    for elem in SVG_DANGEROUS_ELEMENTS:
        if b"<" + elem in content_lower:
            return True

    # Check for dangerous attributes
    for attr in SVG_DANGEROUS_ATTRS:
        if attr + b"=" in content_lower:
            return True

    # Check for javascript: URLs
    if b"javascript:" in content_lower:
        return True

    return False


# Dangerous SVG elements that can execute code
SVG_DANGEROUS_ELEMENTS = {
    b"script",
    b"foreignobject",
    b"iframe",
    b"embed",
    b"object",
    b"use",  # Can reference external files
}

# Dangerous SVG attributes that can execute code
SVG_DANGEROUS_ATTRS = {
    b"onload",
    b"onclick",
    b"onerror",
    b"onmouseover",
    b"onmouseout",
    b"onfocus",
    b"onblur",
    b"onchange",
    b"onsubmit",
    b"onreset",
    b"onkeydown",
    b"onkeyup",
    b"onkeypress",
    b"href",  # Can contain javascript: URLs
    b"xlink:href",
}


def validate_svg_content(content: bytes) -> bool:
    """Validate that SVG content doesn't contain dangerous elements.

    Checks for script tags, event handlers, and other XSS vectors.
    Also checks for encoding bypass attempts (hex entities, unicode entities).

    Args:
        content: The raw SVG file content

    Returns:
        True if SVG is safe, False if it contains dangerous content.
    """
    # Check for encoding declarations that could be used to bypass checks
    # Reject non-UTF-8 encodings that might render differently
    if b"encoding=" in content.lower():
        # Only allow UTF-8 encoding
        if not re.search(rb'encoding\s*=\s*["\']utf-8["\']', content.lower()):
            return False

    # Check for HTML/XML entities that could encode dangerous content
    # These could be used to spell out "script", "javascript", etc.
    # Look for hex entities (&#x...) and decimal entities (&#...)
    entity_pattern = rb'&#x?[0-9a-fA-F]+;'
    if re.search(entity_pattern, content):
        # Decode entities and check the result
        try:
            decoded = _decode_xml_entities(content)
            if _contains_dangerous_content(decoded):
                return False
        except (ValueError, UnicodeDecodeError):
            # If we can't decode, reject as potentially malicious
            return False

    # Note: bytes.lower() is valid in Python 3 and works for ASCII characters.
    # SVG dangerous elements/attributes are ASCII, so this is correct.
    content_lower = content.lower()

    # Check for dangerous elements
    for elem in SVG_DANGEROUS_ELEMENTS:
        # Match opening tags like <script, <SCRIPT, etc.
        if b"<" + elem in content_lower:
            return False

    # Check for dangerous attributes
    for attr in SVG_DANGEROUS_ATTRS:
        # Match attribute patterns like onclick=, ONCLICK=, etc.
        if attr + b"=" in content_lower:
            return False
        if attr + b" " in content_lower:
            return False

    # Check for javascript: URLs
    if b"javascript:" in content_lower:
        return False

    # Check for data: URLs (can embed scripts)
    # Find all data: URLs and verify EACH one is a safe image type
    if b"data:" in content_lower:
        # Pattern to find all data: URLs
        data_urls = re.findall(rb'data:\s*([a-z0-9\-+./]+)', content_lower)
        # Only allow specific safe image types
        safe_mime_types = {
            b"image/png",
            b"image/jpeg",
            b"image/jpg",
            b"image/gif",
            b"image/webp",
            b"image/svg+xml",  # Nested SVGs are validated separately
        }
        for mime_type in data_urls:
            # Normalize by removing whitespace
            mime_clean = mime_type.strip()
            if mime_clean not in safe_mime_types:
                return False

    return True


# Magic bytes (file signatures) for image types
IMAGE_SIGNATURES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],  # RIFF container, verified with WEBP at offset 8
}

# Extension to content type mapping
EXTENSION_TO_CONTENT_TYPE = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def validate_image_signature(content: bytes, content_type: str) -> bool:
    """Validate that file content matches the expected image signature.

    This prevents content-type spoofing attacks where a malicious file
    is uploaded with a fake content-type header.

    Args:
        content: The raw file content bytes
        content_type: The declared MIME type (e.g., "image/jpeg")

    Returns:
        True if the file signature matches the declared content type,
        False otherwise.
    """
    signatures = IMAGE_SIGNATURES.get(content_type)
    if not signatures:
        return False

    # Special handling for WEBP which is a RIFF container
    if content_type == "image/webp":
        # WEBP files: RIFF + 4 bytes size + WEBP
        if content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WEBP":
            return True
        return False

    # Check standard signatures
    for sig in signatures:
        if content.startswith(sig):
            return True

    return False


def get_content_type_from_extension(extension: str) -> str | None:
    """Get the MIME content type for a file extension.

    Args:
        extension: File extension including the dot (e.g., ".jpg")

    Returns:
        MIME type string or None if extension is not supported.
    """
    return EXTENSION_TO_CONTENT_TYPE.get(extension.lower())


def get_extension_from_content_type(content_type: str) -> str:
    """Get the file extension for a MIME content type.

    Args:
        content_type: MIME type (e.g., "image/jpeg")

    Returns:
        File extension including the dot (e.g., ".jpg")
    """
    type_to_ext = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    return type_to_ext.get(content_type, ".jpg")
