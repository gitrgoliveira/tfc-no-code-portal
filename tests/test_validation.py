"""Tests for input validation functions."""

from validation import sanitize_variable_value, validate_url, validate_workspace_name


class TestValidateWorkspaceName:
    """Tests for workspace name validation."""

    def test_valid_workspace_name(self):
        """Test valid workspace names."""
        valid_names = ["my-workspace", "workspace_123", "test-workspace-01", "UPPERCASE", "lowercase", "Mixed_Case-123"]
        for name in valid_names:
            is_valid, error = validate_workspace_name(name)
            assert is_valid, f"'{name}' should be valid but got error: {error}"
            assert error == ""

    def test_empty_workspace_name(self):
        """Test that empty name is invalid."""
        is_valid, error = validate_workspace_name("")
        assert not is_valid
        assert "empty" in error.lower()

    def test_workspace_name_with_special_characters(self):
        """Test that special characters are rejected."""
        invalid_names = ["workspace@123", "work space", "workspace!", "workspace#tag", "workspace.dot"]
        for name in invalid_names:
            is_valid, error = validate_workspace_name(name)
            assert not is_valid, f"'{name}' should be invalid"
            assert "letters, numbers, hyphens, and underscores" in error

    def test_workspace_name_max_length(self):
        """Test maximum length validation."""
        # Test at limit (should pass)
        name_at_limit = "a" * 90
        is_valid, error = validate_workspace_name(name_at_limit)
        assert is_valid

        # Test over limit (should fail)
        name_over_limit = "a" * 91
        is_valid, error = validate_workspace_name(name_over_limit)
        assert not is_valid
        assert "90 characters" in error


class TestValidateUrl:
    """Tests for URL validation."""

    def test_valid_https_url(self):
        """Test valid HTTPS URLs."""
        valid_urls = [
            "https://app.terraform.io",
            "https://terraform.example.com",
            "https://terraform.local:8080",
            "https://terraform.io/path/to/resource",
        ]
        for url in valid_urls:
            is_valid, error = validate_url(url)
            assert is_valid, f"'{url}' should be valid but got error: {error}"
            assert error == ""

    def test_valid_http_url(self):
        """Test valid HTTP URLs."""
        is_valid, error = validate_url("http://terraform.local")
        assert is_valid
        assert error == ""

    def test_empty_url(self):
        """Test that empty URL is invalid."""
        is_valid, error = validate_url("")
        assert not is_valid
        assert "empty" in error.lower()

    def test_url_without_scheme(self):
        """Test that URL without scheme is invalid."""
        is_valid, error = validate_url("app.terraform.io")
        assert not is_valid
        assert "scheme" in error.lower() or "https" in error.lower()

    def test_url_with_invalid_scheme(self):
        """Test that non-http(s) schemes are rejected."""
        invalid_urls = ["ftp://terraform.io", "file:///path/to/file", "ssh://terraform.io"]
        for url in invalid_urls:
            is_valid, error = validate_url(url)
            assert not is_valid, f"'{url}' should be invalid"
            assert "http" in error.lower()


class TestSanitizeVariableValue:
    """Tests for variable value sanitization."""

    def test_sanitize_normal_string(self):
        """Test that normal strings pass through unchanged."""
        value = "normal-string-value-123"
        sanitized = sanitize_variable_value(value)
        assert sanitized == value

    def test_sanitize_empty_string(self):
        """Test that empty string returns empty."""
        assert sanitize_variable_value("") == ""

    def test_sanitize_with_newlines_and_tabs(self):
        """Test that newlines and tabs are preserved."""
        value = "line1\nline2\tindented"
        sanitized = sanitize_variable_value(value)
        assert sanitized == value
        assert "\n" in sanitized
        assert "\t" in sanitized

    def test_sanitize_removes_control_characters(self):
        """Test that control characters are removed."""
        # Create string with control characters (e.g., \x00, \x01)
        value = "text\x00with\x01control\x02chars"
        sanitized = sanitize_variable_value(value)
        assert "\x00" not in sanitized
        assert "\x01" not in sanitized
        assert "\x02" not in sanitized
        assert "textwithcontrolchars" == sanitized

    def test_sanitize_respects_max_length(self):
        """Test that values are truncated to max length."""
        long_value = "a" * 1000
        sanitized = sanitize_variable_value(long_value, max_length=500)
        assert len(sanitized) == 500
        assert sanitized == "a" * 500

    def test_sanitize_unicode_characters(self):
        """Test that unicode characters are preserved."""
        value = "Hello 世界 🌍"
        sanitized = sanitize_variable_value(value)
        assert sanitized == value

    def test_sanitize_default_max_length(self):
        """Test default maximum length (10000)."""
        value = "x" * 15000
        sanitized = sanitize_variable_value(value)
        assert len(sanitized) == 10000
