# AI Agent Instructions for HCP Terraform No-Code Portal

## Project Overview
Streamlit-based web application for deploying HCP Terraform no-code modules. Acts as a user-friendly portal that wraps the Terraform Cloud API (`terrasnek` library) to enable infrastructure deployment without direct HCP Terraform UI interaction.

**Tech Stack**: Python 3.14 (3.11+ supported), Streamlit 1.54.0, terrasnek 0.1.14, pytest, ruff, mypy

## Build, Lint, and Test Commands

### Running the Application
```bash
# Primary method (uses Makefile)
make run                    # Creates venv, installs deps, starts app on port 8501

# Alternative method (shell script)
./run_portal.sh            # Same as above with bash script

# Manual method
source venv/bin/activate
python -m streamlit run portal.py
```

### Dependency Management
`requirements.in` lists direct dependencies (app and dev tools); `requirements.txt` is the lock generated
from it. The lock is universal (`uv pip compile --universal --python-version 3.11`): one file for every OS
and for Python 3.11+. Never regenerate it with plain `pip-compile` or `pip freeze`.
```bash
make update-requirements          # Upgrade every pin in requirements.txt
make upgrade-package PKG=<name>   # Upgrade one pin (e.g. a security fix), keeping the rest unchanged
make requirements                 # Force a reinstall of the venv from requirements.txt
make audit                        # Sync the venv, then audit requirements.txt with pip-audit (also run in CI)
```
Every make target that uses the venv reinstalls it automatically when `requirements.txt` changes. To accept an advisory
that has no fix yet, add `PIP_AUDIT_IGNORE += --ignore-vuln <ID>  # reason, link` in the Makefile (CI uses
the same list).

### Testing
pytest with pytest-cov and pytest-mock, configured in `pyproject.toml`. Tests live in `tests/`
(`test_auth.py`, `test_payload.py`, `test_utils.py`, `test_validation.py`, `test_tooling.py`), with shared
fixtures in `tests/conftest.py`.
```bash
make test          # All tests with coverage
make test-quick    # All tests, no coverage
```

### Running Single Tests
```bash
venv/bin/pytest tests/test_auth.py::TestGetTerraformToken::test_no_token_found -v
venv/bin/pytest tests/test_validation.py -k "workspace_name" -v
```

### Linting, Formatting, Type Checking and Security
All tools are pinned in `requirements.txt` and configured in `pyproject.toml`; CI runs the same versions.
```bash
make lint          # ruff check (pycodestyle, pyflakes, isort, bugbear, bandit, comprehensions, pyupgrade rules)
make format        # ruff format (make format-check to verify only)
make type-check    # mypy
make bandit        # bandit security scan
make verify        # Everything CI runs: lint, format-check, type-check, test, audit, bandit
make pre-commit    # Pre-commit hooks (installed by make install-dev)
```

## Architecture and Project Structure

```
.
├── portal.py              # Main Streamlit application - UI and business logic
├── no_code.py             # Payload generator - workspace creation payloads
├── constants.py           # Application constants and enums
├── utils.py               # Shared helpers (TFC client creation, attribute flattening)
├── validation.py          # Input validation and sanitisation
├── tests/                 # pytest suite (conftest.py + test_*.py)
├── pyproject.toml         # ruff, mypy, bandit, pytest and coverage configuration
├── requirements.in        # Direct dependencies (terrasnek, streamlit, dev tools)
├── requirements.txt       # Universal lock generated from requirements.in (uv pip compile)
├── Makefile               # Build/run/check automation (make help)
├── run_portal.sh          # Alternative startup script
├── .pre-commit-config.yaml
├── .github/
│   ├── copilot-instructions.md  # Detailed AI agent instructions
│   └── workflows/ci.yml         # CI: lint, type-check, test matrix, security scan (+ weekly run)
└── venv/                  # Virtual environment (not in git)
```

### Key Components (portal.py)
- **Authentication** (`get_terraform_token`, `get_credentials_file_path`): Three-tier token discovery (env vars → credentials file → legacy)
- **Module Discovery** (`get_link_list`, `_get_link_list_cached`): Fetch and filter no-code modules from HCP Terraform
- **Settings/Persistence** (`settings`): Sidebar configuration with query param persistence
- **Deployment Workflow** (`no_code_deploy`, `deploy_nocode_module`): Dynamic form generation and workspace creation
- **Display/Orchestration** (`display`): Main UI with two-tab layout

## Code Style Guidelines

### Import Organization
Order: Standard library → Third-party → Local modules, each group sorted (enforced by ruff's isort rules;
`make lint-fix` reorders)
```python
# Standard library (alphabetical)
import json
import logging
import os
import platform
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

# Third-party packages
import streamlit as st
from terrasnek.api import TFC

# Local modules
from no_code import NoCodeDeploy
```

**Rules**:
- ✅ Explicit imports for used functions/classes
- ✅ Minimal aliasing (only `st` for streamlit)
- ❌ No wildcard imports (`from x import *`)
- ❌ No unused imports (e.g., line 12: `# from typing import list`)

### Formatting Conventions

#### String Formatting
Always use **f-strings** (Python 3.6+):
```python
# ✅ Correct
f"Token loaded from environment variable: {env_var_name}"
f"Workspace {ws_name} deployed [here]({api.get_url()}{path})"

# ❌ Avoid
"Token loaded from %s" % env_var_name
"Token loaded from {}".format(env_var_name)
```

#### Line Length and Indentation
- **Indentation**: 4 spaces (no tabs)
- **Line length**: Flexible (~100-120 chars), readability over strict limits
- **Blank lines**: 2 between top-level functions, 1 within functions for logical separation

#### Quotes
- **Strings**: Double quotes `"string"` (enforced by `ruff format`)
- **Docstrings**: Always triple double quotes `"""`

### Type Hints

**Coverage**: Selective/partial (~20% of functions)
- ✅ Always type utility functions and public APIs
- ✅ Use for function signatures that return specific types
- ⚠️ Optional for Streamlit UI functions (hard to type st.session_state)

```python
# ✅ Full type hints for utilities
def get_credentials_file_path() -> Path:
def extract_hostname(url: str) -> str:
def get_terraform_token(url: str = "https://app.terraform.io") -> tuple[str | None, str]:

# ✅ Partial type hints acceptable for complex functions
def show_with_options(api: TFC, module_id: str):  # No return type needed
def deploy_nocode_module(project):                # Complex Streamlit state

# ✅ Type-annotated variables when helpful
api: TFC = st.session_state["api"]
deploy_result: Any
```

**Type hint usage** (built-in generics, as enforced by ruff's pyupgrade rules):
- `X | None` for nullable values
- `tuple[X, Y]`, `list[X]`, `dict[K, V]` for collections
- `Any` for complex/unknown types (use sparingly)
- mypy runs in CI and `make verify`; code must pass `make type-check`

### Naming Conventions

```python
# Constants (module-level)
NUM_COLUMNS = 4           # UPPER_SNAKE_CASE
TFC_TOKEN = os.getenv("TFC_TOKEN", None)

# Variables
module_list = []          # snake_case for all variables
workspace_name = "test"

# Streamlit-specific prefixes
s_project = st.selectbox(...)   # s_* for selectbox variables
b_config = st.button(...)       # b_* for button variables

# Functions
def get_terraform_token():      # verb_noun pattern
def extract_required_variables():  # descriptive, full words (no abbreviations)

# Classes
class NoCodeDeploy:             # PascalCase
```

### Docstrings

**Style**: Google-style docstrings for public functions

```python
def get_terraform_token(url: str = "https://app.terraform.io") -> tuple[str | None, str]:
    """Get Terraform token from multiple sources with priority.

    Priority order:
    1. Environment variable TF_TOKEN_{hostname}
    2. ~/.terraform.d/credentials.tfrc.json file
    3. TFC_TOKEN environment variable (legacy)

    Args:
        url: Terraform Cloud/Enterprise URL

    Returns:
        Tuple of (token, source_description)
    """
```

**Rules**:
- ✅ Required for public functions and complex logic
- ✅ One-line summary followed by blank line and details
- ⚠️ Optional for simple/self-explanatory functions
- ⚠️ Optional for private UI helper functions

### Error Handling

**Strategy**: Defensive with user-friendly messages, graceful degradation

#### Pattern 1: Specific Exception Handling (Preferred)
```python
try:
    with open(creds_file, 'r') as f:
        data = json.load(f)
except json.JSONDecodeError as e:
    logging.warning(f"Invalid JSON in credentials file {creds_file}: {e}")
except PermissionError as e:
    logging.warning(f"Permission denied reading credentials file {creds_file}: {e}")
except Exception as e:
    logging.warning(f"Error reading credentials file {creds_file}: {e}")
```

#### Pattern 2: Broad Exception with UI Feedback
```python
try:
    api = TFC(api_token=token, url=url)
    orgs_list = api.orgs.list()['data']
except Exception as e:
    st.error(f"Invalid token or URL: {str(e)}")
    org = None
```

#### Pattern 3: Guard Clauses (Defensive Checks)
```python
if not st.session_state.get('api', False):
    logging.error("no api configured")
    return []
```

**Rules**:
- ✅ Catch specific exceptions first (JSONDecodeError, PermissionError)
- ✅ Use broad `Exception` as fallback
- ✅ Log warnings for non-critical errors (`logging.warning()`)
- ✅ Show user-facing errors via `st.error()`, `st.warning()`
- ✅ Continue execution when possible (graceful degradation)
- ✅ Use `.get()` with defaults to avoid KeyError
- ❌ No custom exceptions defined in this codebase
- ❌ No validation libraries (pydantic, marshmallow)

### Logging

**Setup** (main entry point):
```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s : %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
```

**Usage**:
- `logging.debug()` - Trace information, API calls
- `logging.warning()` - Non-fatal issues (missing credentials, etc.)
- `logging.error()` - Critical problems preventing operation
- **Streamlit UI**: Use `st.error()`, `st.warning()`, `st.info()`, `st.success()` for user feedback

### State Management

**Two persistence layers**:

```python
# 1. Ephemeral (session state - cleared on refresh)
st.session_state['api']           # TFC API client instance
st.session_state['module_list']   # Cached no-code modules
st.session_state['project_list']  # Cached HCP Terraform projects
st.session_state['deploy_module'] # Currently selected module for deployment

# 2. Persistent (query parameters - survives refresh)
st.query_params['url']            # HCP Terraform URL
st.query_params['org']            # Organization name
st.query_params['project']        # Selected project name
```

**Rules**:
- Use `st.query_params` for user-configurable settings (bookmarkable URLs)
- Use `st.session_state` for API responses and temporary UI state
- Always check existence: `st.session_state.get('api', False)`

## Critical Patterns and Conventions

### Authentication Token Discovery
Three-tier priority matching Terraform CLI behavior (portal.py:51-103):
1. `TF_TOKEN_{hostname}` environment variable (e.g., `TF_TOKEN_app_terraform_io`)
2. `~/.terraform.d/credentials.tfrc.json` (Windows: `%APPDATA%/terraform.d/`)
3. Legacy `TFC_TOKEN` environment variable

### Streamlit UI Layout
```python
NUM_COLUMNS = 4  # Grid layout constant
cols = st.columns(NUM_COLUMNS)
for i, module in enumerate(module_list):
    col = cols[i % NUM_COLUMNS]  # Round-robin column assignment
    col.button(label=module['name'], ...)
```

### API Client Pattern
```python
# Always set organization scope after initialization
api = TFC(api_token=token, url=url)
api.set_org(org)

# Store in session state
st.session_state['api'] = api

# Retrieve with type hint
api: TFC = st.session_state['api']
```

### Form Submission (Prevents Reruns)
```python
deploy_form = st.form(key="deploy_form", border=True)
# ... add form fields ...
b_deploy = deploy_form.form_submit_button("Deploy", type="primary")
if b_deploy:
    # Process form submission
```

## Common Modifications

### Adding New Settings
1. Add input widget in `settings()` function (line 349)
2. Read from `st.query_params.get('key', default_value)`
3. Save on "Apply configuration" button: `st.query_params['key'] = value`
4. Update auto-initialization in `display()` function (lines 413-428)

### Adding New Module Variables
Modify `deploy_nocode_module()` (lines 198-287) and `NoCodeDeploy.generate()` in no_code.py.

Variable attributes: `key`, `value`, `category`, `hcl`, `sensitive`

### Extending Token Sources
Extend `get_terraform_token()` priority chain. Always return `(token, source_description)` tuple.

### Adding API Calls
1. Check for API client: `if not st.session_state.get('api', False): return`
2. Get typed client: `api: TFC = st.session_state['api']`
3. Wrap in try-except with user feedback: `st.error(f"Error: {str(e)}")`

## External Dependencies

### terrasnek (HCP Terraform API Client)
- Organization-scoped: Call `api.set_org()` before operations
- Pagination: `list_all()` methods handle pagination automatically
- Filtering: `filters=[{'keys': ['project', 'id'], 'value': id}]`
- Custom endpoint: `show_with_options()` extends terrasnek for `include=['variable_options']`

### HCP Terraform API Specifics
- No-code modules: `api.no_code_provisioning.deploy(no_code_id, payload=payload)`
- Module relationships: `module['relationships']['no-code-modules']['data'][0]['id']`
- Workspace variables passed as relationships, not attributes

## Git Workflow

```bash
# Check status
git status

# Commit changes (when requested)
git add portal.py no_code.py
git commit -m "Brief description of changes"

# DO NOT push unless explicitly requested
```

**Note**: `.gitignore` excludes all `*.json` files, `venv/`, `__pycache__/`, `.streamlit/`

## Key Reference: Existing Documentation

The `.github/copilot-instructions.md` file (152 lines) contains detailed architectural documentation including:
- Authentication flow details (lines 15-21)
- Settings persistence mechanisms (lines 23-34)
- Module discovery and filtering logic (lines 35-40)
- Dynamic form generation (lines 46-51)
- Session state management (lines 55-63)
- API error handling patterns (lines 65-68)

Always reference this file for architectural decisions and implementation details.
