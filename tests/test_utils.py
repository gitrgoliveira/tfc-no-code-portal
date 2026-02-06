"""Tests for utility functions."""

from typing import Any
from unittest.mock import Mock, patch

from utils import create_tfc_client, flatten_attributes


class TestCreateTfcClient:
    """Tests for TFC client creation."""

    def test_create_tfc_client(self):
        """Test creating a TFC client with organization set."""
        token = "test-token"
        url = "https://app.terraform.io"
        org = "test-org"

        # Patch TFC import to avoid actual API calls
        with patch("utils.TFC") as mock_tfc:
            mock_instance = Mock()
            mock_tfc.return_value = mock_instance

            client = create_tfc_client(token, url, org)

            # Verify TFC was instantiated with correct params
            mock_tfc.assert_called_once_with(api_token=token, url=url)

            # Verify organization was set
            mock_instance.set_org.assert_called_once_with(org)

            # Verify we got the client back
            assert client == mock_instance


class TestFlattenAttributes:
    """Tests for attribute flattening."""

    def test_flatten_basic_attributes(self):
        """Test flattening basic attributes."""
        data = {"id": "test-id", "attributes": {"name": "test-name", "description": "test-description"}}

        result = flatten_attributes(data)

        assert result["id"] == "test-id"
        assert result["name"] == "test-name"
        assert result["description"] == "test-description"

    def test_flatten_with_links(self):
        """Test flattening with links."""
        data = {
            "id": "test-id",
            "attributes": {"name": "test-name"},
            "links": {"self": "/api/v2/resource/test-id", "self-html": "/app/resource/test-id"},
        }

        result = flatten_attributes(data)

        assert result["id"] == "test-id"
        assert result["name"] == "test-name"
        assert result["self"] == "/api/v2/resource/test-id"
        assert result["self-html"] == "/app/resource/test-id"

    def test_flatten_without_links(self):
        """Test flattening when no links present."""
        data = {"id": "test-id", "attributes": {"name": "test-name"}}

        result = flatten_attributes(data)

        assert result["id"] == "test-id"
        assert result["name"] == "test-name"
        assert "links" not in result

    def test_flatten_without_id(self):
        """Test flattening when no ID present."""
        data = {"attributes": {"name": "test-name"}}

        result = flatten_attributes(data)

        assert result["name"] == "test-name"
        assert "id" not in result

    def test_flatten_empty_data(self):
        """Test flattening empty data."""
        data: dict[str, Any] = {}

        result = flatten_attributes(data)

        assert result == {}

    def test_flatten_preserves_nested_data(self):
        """Test that nested data in attributes is preserved."""
        data = {"id": "test-id", "attributes": {"name": "test-name", "config": {"nested": "value"}}}

        result = flatten_attributes(data)

        assert result["name"] == "test-name"
        assert result["config"] == {"nested": "value"}

    def test_flatten_does_not_modify_original(self):
        """Test that flattening doesn't modify original data."""
        data = {"id": "test-id", "attributes": {"name": "test-name"}, "links": {"self": "/api/test"}}

        original_data = data.copy()
        result = flatten_attributes(data)

        # Original should be unchanged
        assert data == original_data
        # But result should be flattened
        assert "attributes" not in result
        assert "links" not in result
