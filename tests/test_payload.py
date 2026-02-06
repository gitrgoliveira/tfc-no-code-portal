"""Tests for NoCodeDeploy payload generator."""

import json

from no_code import NoCodeDeploy


class TestNoCodeDeploy:
    """Tests for the NoCodeDeploy payload generator."""

    def test_generate_basic_payload(self):
        """Test generating a basic payload with no variables."""
        generator = NoCodeDeploy(
            workspace_name="test-workspace", workspace_description="Test description", project_id="prj-123", vars=[]
        )

        payload = generator.generate()

        assert payload["data"]["type"] == "workspaces"
        assert payload["data"]["attributes"]["name"] == "test-workspace"
        assert payload["data"]["attributes"]["description"] == "Test description"
        assert payload["data"]["relationships"]["project"]["data"]["id"] == "prj-123"
        assert payload["data"]["relationships"]["vars"]["data"] == []

    def test_generate_payload_with_variables(self):
        """Test generating payload with variables."""
        vars_list = [
            {"key": "region", "value": "us-east-1", "category": "terraform"},
            {"key": "instance_type", "value": "t2.micro", "category": "terraform"},
        ]

        generator = NoCodeDeploy(
            workspace_name="test-workspace",
            workspace_description="Test description",
            project_id="prj-123",
            vars=vars_list,
        )

        payload = generator.generate()

        vars_data = payload["data"]["relationships"]["vars"]["data"]
        assert len(vars_data) == 2

        # Check first variable
        assert vars_data[0]["type"] == "vars"
        assert vars_data[0]["attributes"]["key"] == "region"
        assert vars_data[0]["attributes"]["value"] == "us-east-1"
        assert vars_data[0]["attributes"]["category"] == "terraform"
        assert vars_data[0]["attributes"]["hcl"] is False
        assert vars_data[0]["attributes"]["sensitive"] is False

    def test_generate_payload_with_sensitive_variables(self):
        """Test generating payload with sensitive variables."""
        vars_list = [{"key": "api_token", "value": "secret", "category": "terraform"}]

        generator = NoCodeDeploy(
            workspace_name="secure-workspace",
            workspace_description="Secure workspace",
            project_id="prj-456",
            vars=vars_list,
        )

        payload = generator.generate()

        # Note: Current implementation always sets sensitive to False
        # This test documents current behavior
        vars_data = payload["data"]["relationships"]["vars"]["data"]
        assert vars_data[0]["attributes"]["sensitive"] is False

    def test_payload_structure(self):
        """Test that payload structure matches HCP Terraform API requirements."""
        generator = NoCodeDeploy(
            workspace_name="structure-test",
            workspace_description="Testing structure",
            project_id="prj-789",
            vars=[{"key": "test", "value": "value", "category": "terraform"}],
        )

        payload = generator.generate()

        # Validate top-level structure
        assert "data" in payload
        assert "type" in payload["data"]
        assert "attributes" in payload["data"]
        assert "relationships" in payload["data"]

        # Validate relationships structure
        relationships = payload["data"]["relationships"]
        assert "project" in relationships
        assert "vars" in relationships
        assert "data" in relationships["project"]
        assert "data" in relationships["vars"]

    def test_payload_is_json_serializable(self):
        """Test that generated payload can be serialized to JSON."""
        generator = NoCodeDeploy(
            workspace_name="json-test",
            workspace_description="JSON serialization test",
            project_id="prj-999",
            vars=[{"key": "key1", "value": "value1", "category": "terraform"}],
        )

        payload = generator.generate()

        # Should not raise exception
        json_str = json.dumps(payload)
        assert isinstance(json_str, str)

        # Should be able to deserialize
        deserialized = json.loads(json_str)
        assert deserialized == payload

    def test_multiple_variables_order_preserved(self):
        """Test that variable order is preserved in payload."""
        vars_list = [
            {"key": "var1", "value": "value1", "category": "terraform"},
            {"key": "var2", "value": "value2", "category": "terraform"},
            {"key": "var3", "value": "value3", "category": "terraform"},
        ]

        generator = NoCodeDeploy(
            workspace_name="order-test", workspace_description="Order test", project_id="prj-order", vars=vars_list
        )

        payload = generator.generate()
        vars_data = payload["data"]["relationships"]["vars"]["data"]

        assert len(vars_data) == 3
        assert vars_data[0]["attributes"]["key"] == "var1"
        assert vars_data[1]["attributes"]["key"] == "var2"
        assert vars_data[2]["attributes"]["key"] == "var3"
