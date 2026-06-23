"""Docstring style validation.

Validates that docstrings conform to a specified style (google, numpy, sphinx).
"""

from glintefy.subservers.common.issues import DocstringIssue

# Style patterns for different docstring formats
STYLE_PATTERNS = {
    "google": {
        "args": ["Args:", "Arguments:"],
        "returns": ["Returns:", "Return:"],
        "raises": ["Raises:", "Raise:"],
        "yields": ["Yields:", "Yield:"],
    },
    "numpy": {
        "args": ["Parameters", "----------"],
        "returns": ["Returns", "-------"],
        "raises": ["Raises", "------"],
        "yields": ["Yields", "------"],
    },
    "sphinx": {
        "args": [":param", ":type"],
        "returns": [":return:", ":rtype:"],
        "raises": [":raises:", ":raise:"],
        "yields": [":yields:"],
    },
}


def get_style_patterns() -> dict:
    """Get docstring style patterns.

    Returns:
        Dictionary mapping style names to their pattern indicators
    """
    return STYLE_PATTERNS


def has_style_indicators(docstring: str, style: str) -> bool:
    """Check if docstring has indicators of a particular style.

    Args:
        docstring: The docstring text to check
        style: Style name (google, numpy, sphinx)

    Returns:
        True if docstring has the style's arg patterns
    """
    if style not in STYLE_PATTERNS:
        return False
    return any(pattern in docstring for pattern in STYLE_PATTERNS[style]["args"])


def detect_used_style(docstring: str, expected_style: str) -> str | None:
    """Detect which style is actually used in the docstring.

    Args:
        docstring: The docstring text to analyze
        expected_style: The expected style to exclude from search

    Returns:
        Name of detected style, or None if no other style detected
    """
    other_styles = [s for s in STYLE_PATTERNS if s != expected_style]
    for other_style in other_styles:
        for patterns in STYLE_PATTERNS[other_style].values():
            if any(pattern in docstring for pattern in patterns):
                return other_style
    return None


def validate_docstring_style(
    docstring: str,
    name: str,
    file_path: str,
    line: int,
    doc_type: str,
    expected_style: str | None,
) -> DocstringIssue | None:
    """Validate docstring conforms to configured style.

    Args:
        docstring: The docstring text
        name: Function/class name
        file_path: File path
        line: Line number
        doc_type: Type of element (function/class)
        expected_style: Expected docstring style (google, numpy, sphinx)

    Returns:
        DocstringIssue if style violation found, None otherwise
    """
    if not docstring or not expected_style:
        return None

    expected = expected_style.lower()

    if expected not in STYLE_PATTERNS:
        return None

    # If expected style is used, no issue
    if has_style_indicators(docstring, expected):
        return None

    # Check if a different style is being used
    used_style = detect_used_style(docstring, expected)
    if used_style:
        return DocstringIssue(
            type="docstring_style_mismatch",
            severity="info",
            file=file_path,
            line=line,
            name=name,
            doc_type=doc_type,
            message=f"{doc_type.capitalize()} '{name}' uses {used_style} style but project expects {expected}",
        )

    return None
