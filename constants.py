"""Application configuration constants for the HCP Terraform No-Code Portal."""

from enum import Enum

# Default Configuration
DEFAULT_TFC_URL = "https://app.terraform.io"
NUM_COLUMNS = 4

# Environment Variable Names
ENV_TOKEN_PREFIX = "TF_TOKEN_"
ENV_LEGACY_TOKEN = "TFC_TOKEN"
ENV_TFC_URL = "TFC/E_URL"


class SessionKeys(str, Enum):
    """Session state keys for Streamlit application."""

    API = "api"
    MODULE_LIST = "module_list"
    PROJECT_LIST = "project_list"
    DEPLOY_MODULE = "deploy_module"


class QueryParamKeys(str, Enum):
    """Query parameter keys for URL persistence."""

    URL = "url"
    ORG = "org"
    PROJECT = "project"


# Terraform Naming Rules
WORKSPACE_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"
WORKSPACE_NAME_MAX_LENGTH = 90
