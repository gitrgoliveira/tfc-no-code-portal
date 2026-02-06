"""Test configuration and fixtures for pytest."""

import json
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_tfc_client():
    """Create a mock TFC client for testing."""
    client = Mock()
    client.get_url.return_value = "https://app.terraform.io"
    client.get_hostname.return_value = "app.terraform.io"
    client.get_org.return_value = "test-org"
    client.set_org = Mock()
    return client


@pytest.fixture
def sample_module_data():
    """Sample module data from TFC API."""
    return {
        "id": "mod-123",
        "type": "registry-modules",
        "attributes": {
            "name": "test-module",
            "namespace": "test-org",
            "provider": "aws",
            "no-code": True,
            "version-statuses": [{"version": "1.0.0"}],
        },
        "relationships": {"no-code-modules": {"data": [{"id": "nocode-123", "type": "no-code-module"}]}},
    }


@pytest.fixture
def sample_workspace_data():
    """Sample workspace data from TFC API."""
    return {
        "id": "ws-123",
        "type": "workspaces",
        "attributes": {
            "name": "test-workspace",
            "description": "Test workspace",
            "tag-names": ["test"],
            "source": "no-code",
            "source-module-id": "mod-123",
        },
        "links": {"self-html": "/app/test-org/workspaces/test-workspace"},
    }


@pytest.fixture
def sample_project_data():
    """Sample project data from TFC API."""
    return {
        "data": [
            {
                "id": "prj-123",
                "type": "projects",
                "attributes": {"name": "Default Project", "description": "Test project"},
            }
        ]
    }


@pytest.fixture
def sample_registry_metadata():
    """Sample registry metadata with input variables."""
    return {
        "data": {
            "attributes": {
                "input-variables": [
                    {
                        "name": "region",
                        "type": "string",
                        "description": "AWS region",
                        "required": True,
                        "sensitive": False,
                    },
                    {
                        "name": "access_key",
                        "type": "string",
                        "description": "AWS access key",
                        "required": True,
                        "sensitive": True,
                    },
                    {
                        "name": "optional_var",
                        "type": "string",
                        "description": "Optional variable",
                        "required": False,
                        "sensitive": False,
                    },
                ]
            }
        }
    }


@pytest.fixture
def temp_credentials_file(tmp_path):
    """Create a temporary credentials file for testing."""
    creds_dir = tmp_path / ".terraform.d"
    creds_dir.mkdir()
    creds_file = creds_dir / "credentials.tfrc.json"

    creds_data = {"credentials": {"app.terraform.io": {"token": "test-token-from-file"}}}

    creds_file.write_text(json.dumps(creds_data))
    return creds_file


@pytest.fixture
def mock_env_token(monkeypatch):
    """Set up environment variable for TFC token."""
    monkeypatch.setenv("TF_TOKEN_app_terraform_io", "test-token-from-env")
    return "test-token-from-env"
