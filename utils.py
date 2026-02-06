"""Utility functions for the HCP Terraform No-Code Portal."""

from typing import Any

import streamlit as st
from terrasnek.api import TFC

from constants import SessionKeys


def get_session_api_client() -> TFC | None:
    """Get the TFC API client from session state.

    Returns:
        TFC client instance or None if not configured
    """
    return st.session_state.get(SessionKeys.API, None)


def create_tfc_client(token: str, url: str, org: str) -> TFC:
    """Create and configure a TFC API client.

    Args:
        token: API token
        url: TFC/TFE URL
        org: Organization name

    Returns:
        Configured TFC client instance
    """
    api = TFC(api_token=token, url=url)
    api.set_org(org)
    return api


def flatten_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested attributes and links into a single dictionary.

    This is useful for converting API responses into Streamlit-friendly
    flat dictionaries for dataframes.

    Args:
        data: Dictionary with nested 'attributes' and 'links' keys

    Returns:
        Flattened dictionary with attributes and links merged
    """
    attributes: dict[str, Any] = data.get("attributes", {})
    flattened = attributes.copy()

    # Add ID if present
    if "id" in data:
        flattened["id"] = data["id"]

    # Merge links
    if "links" in data:
        links: dict[str, Any] = data["links"]
        flattened.update(links)

    return flattened
