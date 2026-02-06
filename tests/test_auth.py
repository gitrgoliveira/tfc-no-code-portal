"""Tests for authentication and token discovery."""

import json
from unittest.mock import patch

from portal import extract_hostname, get_credentials_file_path, get_terraform_token


class TestExtractHostname:
    """Tests for hostname extraction from URLs."""

    def test_extract_hostname_with_protocol(self):
        """Test extracting hostname from URL with https protocol."""
        assert extract_hostname("https://app.terraform.io") == "app.terraform.io"

    def test_extract_hostname_with_http(self):
        """Test extracting hostname from URL with http protocol."""
        assert extract_hostname("http://terraform.example.com") == "terraform.example.com"

    def test_extract_hostname_with_port(self):
        """Test extracting hostname from URL with port number."""
        assert extract_hostname("https://terraform.local:8080") == "terraform.local"

    def test_extract_hostname_without_protocol(self):
        """Test extracting hostname from URL without protocol."""
        assert extract_hostname("app.terraform.io") == "app.terraform.io"

    def test_extract_hostname_case_insensitive(self):
        """Test that hostname extraction is case-insensitive."""
        assert extract_hostname("https://APP.TERRAFORM.IO") == "app.terraform.io"


class TestGetCredentialsFilePath:
    """Tests for credentials file path resolution."""

    @patch("platform.system")
    def test_credentials_path_linux(self, mock_system):
        """Test credentials path on Linux."""
        mock_system.return_value = "Linux"
        path = get_credentials_file_path()
        assert str(path).endswith(".terraform.d/credentials.tfrc.json")

    @patch("platform.system")
    @patch("os.getenv")
    def test_credentials_path_windows(self, mock_getenv, mock_system):
        """Test credentials path on Windows."""
        mock_system.return_value = "Windows"
        mock_getenv.return_value = "C:\\Users\\Test\\AppData\\Roaming"
        path = get_credentials_file_path()
        assert "terraform.d" in str(path)
        assert "credentials.tfrc.json" in str(path)


class TestGetTerraformToken:
    """Tests for token discovery with multiple sources."""

    def test_token_from_environment_variable(self, monkeypatch):
        """Test loading token from TF_TOKEN_* environment variable."""
        monkeypatch.setenv("TF_TOKEN_app_terraform_io", "env-token-123")
        token, source = get_terraform_token("https://app.terraform.io")
        assert token == "env-token-123"
        assert "Environment Variable" in source
        assert "TF_TOKEN_app_terraform_io" in source

    def test_token_from_credentials_file(self, tmp_path, monkeypatch):
        """Test loading token from credentials file."""
        # Clear environment variables
        monkeypatch.delenv("TF_TOKEN_app_terraform_io", raising=False)
        monkeypatch.delenv("TFC_TOKEN", raising=False)

        # Create mock credentials file
        creds_file = tmp_path / "credentials.tfrc.json"
        creds_data = {"credentials": {"app.terraform.io": {"token": "file-token-456"}}}
        creds_file.write_text(json.dumps(creds_data))

        # Mock get_credentials_file_path to return our temp file
        with patch("portal.get_credentials_file_path", return_value=creds_file):
            token, source = get_terraform_token("https://app.terraform.io")
            assert token == "file-token-456"
            assert "Credentials File" in source

    def test_token_from_legacy_env_variable(self, monkeypatch, tmp_path):
        """Test loading token from legacy TFC_TOKEN environment variable."""
        # Clear preferred env variables
        monkeypatch.delenv("TF_TOKEN_app_terraform_io", raising=False)
        monkeypatch.setenv("TFC_TOKEN", "legacy-token-789")

        # Mock non-existent credentials file
        non_existent = tmp_path / "nonexistent.json"
        with patch("portal.get_credentials_file_path", return_value=non_existent):
            token, source = get_terraform_token("https://app.terraform.io")
            assert token == "legacy-token-789"
            assert "TFC_TOKEN" in source

    def test_no_token_found(self, monkeypatch, tmp_path):
        """Test when no token is found from any source."""
        # Clear all environment variables
        monkeypatch.delenv("TF_TOKEN_app_terraform_io", raising=False)
        monkeypatch.delenv("TFC_TOKEN", raising=False)

        # Mock non-existent credentials file
        non_existent = tmp_path / "nonexistent.json"
        with patch("portal.get_credentials_file_path", return_value=non_existent):
            token, source = get_terraform_token("https://app.terraform.io")
            assert token is None
            assert "Not Found" in source

    def test_token_priority_env_over_file(self, monkeypatch, tmp_path):
        """Test that environment variable takes priority over file."""
        monkeypatch.setenv("TF_TOKEN_app_terraform_io", "env-token-priority")

        # Create credentials file
        creds_file = tmp_path / "credentials.tfrc.json"
        creds_data = {"credentials": {"app.terraform.io": {"token": "file-token-lower-priority"}}}
        creds_file.write_text(json.dumps(creds_data))

        with patch("portal.get_credentials_file_path", return_value=creds_file):
            token, source = get_terraform_token("https://app.terraform.io")
            assert token == "env-token-priority"
            assert "Environment Variable" in source

    def test_invalid_json_in_credentials_file(self, monkeypatch, tmp_path):
        """Test handling of invalid JSON in credentials file."""
        monkeypatch.delenv("TF_TOKEN_app_terraform_io", raising=False)
        monkeypatch.delenv("TFC_TOKEN", raising=False)

        # Create file with invalid JSON
        creds_file = tmp_path / "credentials.tfrc.json"
        creds_file.write_text("{invalid json content")

        with patch("portal.get_credentials_file_path", return_value=creds_file):
            token, source = get_terraform_token("https://app.terraform.io")
            assert token is None
            assert "Not Found" in source
