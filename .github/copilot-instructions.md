# AI Agent Instructions for HCP Terraform No-Code Portal

## Project Overview
Streamlit-based web application for deploying HCP Terraform no-code modules. Acts as a user-friendly portal that wraps the Terraform Cloud API (`terrasnek` library) to enable infrastructure deployment without direct HCP Terraform UI interaction.

## Architecture
- **Single-file Streamlit app**: `portal.py` (~458 lines) contains all UI and business logic
- **Payload generator**: `no_code.py` - simple class that constructs HCP Terraform workspace payloads
- **State management**: Uses `st.session_state` to cache API client, module lists, and project data
- **Settings persistence**: URL query parameters persist sidebar settings across page refreshes
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

### Session State Management
```python
st.session_state['api']           # TFC client (set on "Apply configuration")
st.session_state['module_list']   # Cached no-code modules
st.session_state['project_list']  # Cached HCP Terraform projects
st.session_state['deploy_module'] # Currently selected module for deployment
```

**Persistence Strategy**: Session state is ephemeral (cleared on refresh). Use `st.query_params` for persistent settings, session state for cached API responses.

### API Error Handling
- **Sidebar settings**: Catch `Exception` and display error when fetching orgs (line 388)
- **Module deployment**: Try-except with spinner, show success link or error (lines 259-287)
- **Missing API**: Check `st.session_state.get('api', False)` before all API calls

### Workspace Data Flattening (lines 301-318)
HCP Terraform API returns nested structures. Code flattens for Streamlit dataframes:
```python
ws['attributes'].update(ws['links'])  # Merge nested dicts
ws['self-html'] = api.get_url() + ws['self-html']  # Make absolute URLs
```

## Development Workflows

### Setup & Run
```bash
make requirements  # Creates venv, pip-compile, installs deps
make run          # Starts Streamlit on default port 8501
# OR
./run_portal.sh   # Alternative shell script
```

### Dependency Management
- **Pin dependencies**: Edit `requirements.in` (only `terrasnek` and `streamlit`)
- **Update lock file**: `make requirements` runs `pip-compile`
- **Do not** manually edit `requirements.txt` (auto-generated)

### Debugging
- Set `log_level=logging.DEBUG` in TFC client (commented line 389)
- Check terminal output for API calls and credential discovery logs
- Use `st.json()` for inspecting API responses (see commented examples lines 209-211)

## Project-Specific Conventions

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
