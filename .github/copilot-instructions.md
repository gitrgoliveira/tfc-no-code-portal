# AI Agent Instructions for HCP Terraform No-Code Portal

## Project Overview
Production-ready Streamlit web application for deploying HCP Terraform no-code modules. Wraps the Terraform Cloud API (`terrasnek`) to enable infrastructure deployment through an intuitive UI without direct HCP Terraform interaction.

**Stack**: Python 3.11-3.14, Streamlit 1.54.0, terrasnek 0.1.14, pytest, ruff, mypy

## Architecture (Modular Design - 6 Core Modules)

### Core Application Files
- **`portal.py`** (~460 lines) - Main Streamlit UI and business logic
- **`no_code.py`** (~60 lines) - Workspace payload generator (`NoCodeDeploy` class)
- **`constants.py`** (~30 lines) - Configuration constants, enums (`SessionKeys`, `QueryParamKeys`)
- **`validation.py`** (~80 lines) - Input validation (`validate_workspace_name`, `validate_url`, `sanitize_variable_value`)
- **`utils.py`** (~65 lines) - Reusable utilities (`create_tfc_client`, `flatten_attributes`, `get_session_api_client`)

### State Management & Persistence
- **Ephemeral**: `st.session_state` for API client, cached modules/projects, selected deployment
- **Persistent**: `st.query_params` for settings (URL, org, project) that survive page refresh
- **API wrapper**: `terrasnek.api.TFC` client handles all HCP Terraform REST API calls

## Key Components & Data Flow

### Authentication (lines 20-103 in portal.py)
Three-tier credential discovery matching Terraform CLI behavior:
1. `TF_TOKEN_{hostname}` environment variable (e.g., `TF_TOKEN_app_terraform_io`)
2. `~/.terraform.d/credentials.tfrc.json` (cross-platform: Windows uses `%APPDATA%`)
3. Legacy `TFC_TOKEN` environment variable

**Pattern**: Always use `get_terraform_token(url)` which returns `(token, source_description)` tuple for UI display.

### Settings Persistence (lines 349-409)
URL query parameters persist non-sensitive settings across page refreshes:
- `?url=` - HCP Terraform URL
- `?org=` - Organization name  
- `?project=` - Selected project ID

**Auto-initialization**: On page load, `display()` function (lines 412-430) checks for saved query params and auto-restores API client if token discoverable.

**Buttons**:
- **"Apply configuration"** (primary) - Saves settings to query params, creates API client
- **"Clear cache and refresh"** (secondary) - Clears all `st.session_state` and calls `st.rerun()`

### Module Discovery & Filtering (lines 111-145)
`get_link_list()` fetches all registry modules and filters by `['attributes']['no-code'] == True`:
- Handles both private and public modules (distinguished by `version-statuses` presence)
- Builds HCP Terraform UI links: `https://{hostname}/app/{org}/registry/modules/{origin}/...`
- Creates registry metadata links for variable introspection
- Returns list of dicts: `{'name': str, 'link': str, 'data': dict, 'registry_link': str}`

### Two-Tab UI Pattern (lines 437-457)
1. **"HCP Terraform Workflow"**: Direct links to HCP Terraform UI for standard workflow
2. **"Direct Module Deployment"**: In-app deployment with dynamic form generation

### Dynamic Form Generation (lines 198-287)
`deploy_nocode_module()` introspects module metadata to build forms:
- Calls `extract_required_variables()` to parse registry metadata
- Dynamically creates text inputs based on variable sensitivity (password vs default type)
- Constructs workspace payload via `NoCodeDeploy.generate()`
- Deploys using `api.no_code_provisioning.deploy()`

## Critical Patterns

### Input Validation (validation.py)
All user input flows through validation functions:
```python
from validation import validate_workspace_name, validate_url, sanitize_variable_value

# Workspace names (alphanumeric + hyphens/underscores)
is_valid, error_msg = validate_workspace_name(name)
if not is_valid:
    st.error(error_msg)

# URLs with scheme check
is_valid, error_msg = validate_url(url)

# Variable sanitization (strips whitespace, None → empty string)
clean_value = sanitize_variable_value(raw_input)
```

### Constants Usage (constants.py)
Replace magic strings with enums:
```python
from constants import SessionKeys, QueryParamKeys, ENV_TOKEN_PREFIX, WORKSPACE_NAME_PATTERN

# Session state access
api = st.session_state.get(SessionKeys.API.value, None)
modules = st.session_state.get(SessionKeys.MODULE_LIST.value, [])

# Query params
url = st.query_params.get(QueryParamKeys.URL.value, "https://app.terraform.io")

# Environment variables
token = os.getenv(f"{ENV_TOKEN_PREFIX}{hostname_normalized}")
```

### Utility Functions (utils.py)
```python
from utils import create_tfc_client, flatten_attributes, get_session_api_client

# API client creation (validates inputs first)
api, error = create_tfc_client(token, url)
if error:
    st.error(error)
    return

# Retrieve from session state with type checking
api = get_session_api_client()
if not api:
    st.warning("Configure API settings first")
    return

# Flatten nested API responses for Streamlit dataframes
workspaces = [flatten_attributes(ws) for ws in api.workspaces.list_all()['data']]
```

### Dynamic Form Keys (Anti-Pattern Fix)
Use dynamic keys for form inputs to clear cached values when context changes:
```python
# ❌ OLD: Static key causes stale values
ws_name = st.text_input("Workspace Name", key="ws_name")

# ✅ NEW: Dynamic key resets when module changes
deploy_module_name = st.session_state[SessionKeys.DEPLOY_MODULE.value]['name']
ws_name = st.text_input("Workspace Name", key=f"ws_name_{deploy_module_name}")
```

### Streamlit API Updates
Use current Streamlit 1.54+ API (deprecated methods removed 2025-12-31):
```python
# ❌ OLD: Deprecated
st.dataframe(..., use_container_width=True)

# ✅ NEW: Replacement
st.dataframe(..., width="stretch")
```

## Development Workflows

### Essential Commands (Makefile - 13 targets)
```bash
make help               # Show all available commands
make run                # Start Streamlit app (auto-installs deps in venv)
make test               # Run pytest with coverage
make test-quick         # Run tests without coverage (faster)
make lint               # Check code with ruff
make lint-fix           # Auto-fix linting issues
make format             # Format code with ruff
make type-check         # Run mypy static analysis
make verify             # Run all checks (lint + type + test)
make clean              # Remove venv and generated files
make requirements       # Install/sync deps from requirements.txt
make update-requirements # Recompile requirements.txt from requirements.in
make install-dev        # Setup pre-commit hooks
```

**Critical**: All tools run from `venv/` - never use system Python. Makefile auto-creates venv on first run.

### Testing & Quality Gates
- **Tests**: 43 tests in `tests/` (test_auth, test_validation, test_payload, test_utils)
- **Coverage**: 41% overall, 100% for new modules (constants, validation, utils)
- **Pre-commit hooks**: Auto-run ruff lint/format + mypy on commit
- **CI/CD**: `.github/workflows/ci.yml` runs 4 parallel jobs (lint, type, test, security)

### Dependency Management
- **Lock file**: `requirements.txt` (146 packages, auto-generated by pip-compile)
- **Source**: `requirements.in` (only direct deps: terrasnek, streamlit, dev tools)
- **Update**: Edit `requirements.in` → run `make update-requirements` → commit both files

## Project-Specific Conventions

### Testing Patterns
All new code must have tests. Target: 90%+ coverage for new modules.

```python
# Fixture usage (conftest.py)
def test_validation(sample_workspace_name):
    """Use shared fixtures from conftest.py"""
    is_valid, _ = validate_workspace_name(sample_workspace_name)
    assert is_valid

# Mocking external APIs (test_auth.py)
@patch.dict(os.environ, {"TF_TOKEN_app_terraform_io": "test-token"})
def test_env_token_discovery():
    token, source = get_terraform_token("https://app.terraform.io")
    assert token == "test-token"

# Parametrized tests (test_validation.py)
@pytest.mark.parametrize("name,expected", [
    ("valid-name", True),
    ("invalid name", False),
    ("", False),
])
def test_workspace_names(name, expected):
    is_valid, _ = validate_workspace_name(name)
    assert is_valid == expected
```

**Run tests**: `make test` (with coverage) or `make test-quick` (faster)

### Variable Naming
- `s_*` prefix: Streamlit selectbox values (e.g., `s_project`)
- `b_*` prefix: Button variables (e.g., `b_deploy`, `b_config`, `b_clear`)
- `api: TFC`: Type-hinted API client instances

### Column Layout Pattern
```python
NUM_COLUMNS = 4  # Grid layout constant
cols = st.columns(NUM_COLUMNS)
col = cols[i % NUM_COLUMNS]  # Round-robin column assignment
```

### Registry Link Construction
Two registry API versions used:
- **v2 metadata** (preferred): `/registry/{origin}/v2/modules/.../metadata/{version}`
- **v1 download** (legacy, commented): `/registry/v1/modules/.../download`

### Form Submission Pattern
Use `st.form()` with `form_submit_button()` for multi-field deployments to prevent per-input reruns (lines 198-287).

## External Integrations

### terrasnek Library
- **Organization scope**: Must call `api.set_org()` before most operations
- **Filtering**: Use `filters=[{'keys': ['project', 'id'], 'value': id}]` for workspace queries
- **Pagination**: `list_all()` methods handle pagination automatically
- **Custom endpoint**: `show_with_options()` extends terrasnek with `include=['variable_options']`

### HCP Terraform API Specifics
- No-code modules require special endpoint: `api.no_code_provisioning.deploy()`
- Module relationships: `module['relationships']['no-code-modules']['data'][0]['id']`
- Workspace variables passed as relationships, not attributes in payload

## When Making Changes

### Adding New Validation Rules
1. Add validation function to `validation.py` following existing patterns
2. Write tests in `tests/test_validation.py` (use parametrize for multiple cases)
3. Import and use in `portal.py` before processing user input
4. Update constants in `constants.py` if new patterns needed (e.g., regex)

### Adding New Constants
1. Add to appropriate enum in `constants.py` (SessionKeys, QueryParamKeys)
2. Replace magic strings throughout codebase with enum references
3. Write tests if constant has validation logic

### Adding New Utility Functions
1. Add to `utils.py` with full type hints and docstrings
2. Write comprehensive tests in `tests/test_utils.py`
3. Target 90%+ coverage for new utilities

### Adding Token Sources
Extend `get_terraform_token()` priority chain. Always return `(token, source_description)` tuple for UI display.

### Adding Persistent Settings
- Write to `st.query_params['key'] = value` in `settings()` when "Apply configuration" clicked
- Read from `st.query_params.get('key')` to set defaults in input widgets
- Update auto-initialization logic in `display()` function (lines 413-428)

### Adding Module Metadata
Extend `show_with_options()` include parameter, not `api.registry_modules` methods (custom endpoint needed).

### UI State Changes
- Non-persistent data: Store in `st.session_state`
- Persistent settings: Use `st.query_params` for bookmarkable/shareable URLs
- Clear cache button clears session state and calls `st.rerun()`

### Form Fields
Modify `deploy_nocode_module()` and `NoCodeDeploy.generate()`. Variable attributes: `key`, `value`, `category`, `hcl`, `sensitive`.

### Quality Checklist
Before committing:
```bash
make verify  # Run lint + type-check + tests
# OR manually:
make lint           # ruff check
make type-check     # mypy
make test           # pytest with coverage
```

Pre-commit hooks will auto-run on `git commit` - ensure they pass.
