"""Input validation utilities for the HCP Terraform No-Code Portal."""

import re
from urllib.parse import urlparse

from constants import WORKSPACE_NAME_MAX_LENGTH, WORKSPACE_NAME_PATTERN


def validate_workspace_name(name: str) -> tuple[bool, str]:
    """Validate workspace name according to Terraform naming rules.

    Workspace names must:
    - Contain only letters, numbers, hyphens, and underscores
    - Not exceed 90 characters

    Args:
        name: Workspace name to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Workspace name cannot be empty"

    if len(name) > WORKSPACE_NAME_MAX_LENGTH:
        return False, f"Workspace name must not exceed {WORKSPACE_NAME_MAX_LENGTH} characters"

    if not re.match(WORKSPACE_NAME_PATTERN, name):
        return False, "Workspace name must contain only letters, numbers, hyphens, and underscores"

    return True, ""


def validate_url(url: str) -> tuple[bool, str]:
    """Validate URL format.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"

    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL format. Must include scheme (https://) and hostname"

        if result.scheme not in ["http", "https"]:
            return False, "URL must use http or https protocol"

        return True, ""
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def sanitize_variable_value(value: str, max_length: int = 10000) -> str:
    """Sanitize variable values for API submission.

    Args:
        value: Variable value to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized value (trimmed if necessary)
    """
    if not value:
        return ""

    # Trim to max length
    sanitized = value[:max_length]

    # Remove any control characters except newlines and tabs
    sanitized = "".join(char for char in sanitized if char.isprintable() or char in "\n\t")

    return sanitized
