import json
import logging
import os
import platform
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import streamlit as st
from terrasnek.api import TFC

from constants import (
    DEFAULT_TFC_URL,
    ENV_LEGACY_TOKEN,
    ENV_TFC_URL,
    ENV_TOKEN_PREFIX,
    NUM_COLUMNS,
    QueryParamKeys,
    SessionKeys,
)
from no_code import NoCodeDeploy
from utils import create_tfc_client
from validation import sanitize_variable_value, validate_workspace_name


@st.cache_data(ttl=300)
def get_credentials_file_path() -> Path:
    """Get the Terraform credentials file path based on OS.

    Returns:
        Path to credentials.tfrc.json file
    """
    home = Path.home()
    if platform.system() == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "terraform.d" / "credentials.tfrc.json"
    return home / ".terraform.d" / "credentials.tfrc.json"


@st.cache_data
def extract_hostname(url: str) -> str:
    """Extract hostname from URL for credential lookup.

    Args:
        url: Full URL (e.g., 'https://app.terraform.io')

    Returns:
        Hostname without protocol (e.g., 'app.terraform.io')
    """
    parsed = urlparse(url)
    hostname = parsed.netloc if parsed.netloc else parsed.path.split("/")[0]
    # Remove port if present
    if ":" in hostname:
        hostname = hostname.split(":")[0]
    return hostname.lower().strip("/")


@st.cache_data(ttl=300)
def get_terraform_token(url: str = DEFAULT_TFC_URL) -> tuple[str | None, str]:
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
    hostname = extract_hostname(url)

    # Try environment variable TF_TOKEN_{hostname} (highest priority)
    env_var_name = f"{ENV_TOKEN_PREFIX}{hostname.replace('.', '_').replace('-', '__')}"
    token = os.getenv(env_var_name)
    if token and token.strip():
        logging.debug(f"Token loaded from environment variable: {env_var_name}")
        return token.strip(), f"Environment Variable ({env_var_name})"

    # Try credentials file
    creds_file = get_credentials_file_path()
    if creds_file.exists():
        try:
            with open(creds_file) as f:
                data = json.load(f)
                credentials = data.get("credentials", {})
                host_creds = credentials.get(hostname, {})
                token = host_creds.get("token")
                if token and token.strip():
                    logging.debug(f"Token loaded from credentials file for hostname: {hostname}")
                    return token.strip(), f"Credentials File ({creds_file})"
        except (json.JSONDecodeError, PermissionError, OSError) as e:
            logging.warning(f"Error reading credentials file {creds_file}: {e}")
    else:
        logging.debug(f"Credentials file not found: {creds_file}")

    # Fallback to legacy environment variable
    token = os.getenv(ENV_LEGACY_TOKEN)
    if token and token.strip():
        logging.debug("Token loaded from legacy TFC_TOKEN environment variable")
        return token.strip(), f"Environment Variable ({ENV_LEGACY_TOKEN})"

    logging.debug("No token found from any source")
    return None, "Not Found (Manual Entry Required)"


@st.cache_data(ttl=600, hash_funcs={"terrasnek.api.TFC": id})
def _get_link_list_cached(url: str, token: str, org: str) -> list[dict[str, Any]]:
    """Cached module list retrieval.

    Args:
        url: HCP Terraform URL
        token: API token
        org: Organization name

    Returns:
        List of no-code modules with metadata
    """
    api = create_tfc_client(token, url, org)
    if not api:
        return []

    no_code_list = []
    ## get all the modules from Terraform Cloud
    module_list = api.registry_modules.list_all()
    hostname = api.get_hostname()
    organization = api.get_org()
    for module in module_list["data"]:
        ## filter by which ones are marked as no code
        if module["attributes"]["no-code"]:
            attr = module["attributes"]
            latest_version = ""
            registry_origin = "private"
            no_code_module_id = module["relationships"]["no-code-modules"]["data"][0]["id"]
            no_code_module = _show_with_options_cached(url, token, org, no_code_module_id)
            if len(attr["version-statuses"]) == 0:
                logging.warning(f"No version detected. May be a public module:\n {module}")
                logging.warning(no_code_module)
                registry_origin = "public"
                latest_version = no_code_module["data"]["attributes"]["version-pin"]
            else:
                latest_version = attr["version-statuses"][0]["version"]
            link = f"https://{hostname}/app/{organization}/registry/modules/{registry_origin}/{attr['namespace']}/{attr['name']}/{attr['provider']}/{latest_version}/new-workspace"
            registry_link = f"https://{hostname}/api/registry/{registry_origin}/v2/modules/{attr['namespace']}/{attr['name']}/{attr['provider']}/metadata/{latest_version}?organization_name={organization}"
            no_code_list.append(
                {"name": attr["name"], "link": link, "data": no_code_module, "registry_link": registry_link}
            )

    return no_code_list


def get_link_list() -> list[dict[str, Any]]:
    if not st.session_state.get(SessionKeys.API, False):
        logging.error("no api configured")
        return []

    api: TFC = st.session_state[SessionKeys.API]
    url = api.get_url()
    org = str(api.get_org())  # Safe cast - API validated before this point
    token = str(api._token)  # Safe cast - API validated before this point

    return _get_link_list_cached(url, token, org)


def display_list() -> None:
    st.markdown(
        "_Start a no code module workflow with HCP Terraform_",
    )
    cols = st.columns(NUM_COLUMNS)
    for i, module in enumerate(st.session_state[SessionKeys.MODULE_LIST]):
        col = cols[i % NUM_COLUMNS]
        col.link_button(label=module["name"], url=module["link"], width="stretch", type="primary")


def no_code_deploy() -> None:

    if not st.session_state.get(SessionKeys.API, False):
        st.warning("no api configured")
        return

    # Get project names and check for saved selection
    project_names = get_project_names()
    saved_project = st.query_params.get(QueryParamKeys.PROJECT)
    default_project_index = 0
    if saved_project and saved_project in project_names:
        default_project_index = project_names.index(saved_project)

    s_project = st.selectbox("Target Project", project_names, index=default_project_index, key="project_select")

    # Persist project selection to query params
    if s_project:
        st.query_params[QueryParamKeys.PROJECT] = s_project

    st.markdown("## Infrastructure to deploy")
    cols = st.columns(NUM_COLUMNS)
    for i, module in enumerate(st.session_state[SessionKeys.MODULE_LIST]):
        col = cols[i % NUM_COLUMNS]
        if col.button(label=module["name"], use_container_width=True, type="primary"):
            st.session_state[SessionKeys.DEPLOY_MODULE] = (module["name"], module["data"], module["registry_link"])

    st.divider()
    if s_project:
        st.markdown("## Current infrastructure")
        project = get_project_by_name(s_project)
        if project is not None:
            st.write(project["attributes"].get("description", "no project description"))
            # st.write(api.projects.show(project['id']))
            display_workspaces(project["id"])
            if SessionKeys.DEPLOY_MODULE in st.session_state:
                deploy_nocode_module(project)


@st.cache_data(ttl=600, hash_funcs={"terrasnek.api.TFC": id})
def _show_with_options_cached(url: str, token: str, org: str, module_id: str) -> dict[str, Any]:
    """Cached no-code module options retrieval.

    Args:
        url: HCP Terraform URL
        token: API token
        org: Organization name
        module_id: No-code module ID

    Returns:
        Module options data
    """
    api = create_tfc_client(token, url, org)
    if not api:
        return {}

    api_url = f"{api.no_code_provisioning._no_code_base_url}/{module_id}"
    return api.no_code_provisioning._show(url=api_url, include=["variable_options"])  # type: ignore[no-any-return]


def show_with_options(api: TFC, module_id: str):
    url = api.get_url()
    org = str(api.get_org())  # Safe cast - API validated before this point
    token = str(api._token)  # Safe cast - API validated before this point
    return _show_with_options_cached(url, token, org, module_id)


def deploy_nocode_module(project: dict[str, Any]) -> None:

    deploy_form = st.form(key="deploy_form", border=True)
    api: TFC = st.session_state[SessionKeys.API]
    (deploy_module_name, deploy_module_data, deploy_module_registry_link) = st.session_state[SessionKeys.DEPLOY_MODULE]
    no_code_id = deploy_module_data["data"]["id"]

    deploy_form.markdown(f"## Deploy {deploy_module_name}")
    # random_chars = ''.join(random.choice(string.ascii_letters) for _ in range(3))

    ws_name = deploy_form.text_input(
        "Workspace name", key=f"ws_name_{deploy_module_name}", value=f"{deploy_module_name}-"
    )

    # Validate workspace name
    is_valid, error_msg = validate_workspace_name(ws_name)
    if not is_valid and ws_name:
        deploy_form.error(f"❌ {error_msg}")
    elif ws_name:
        deploy_form.success("✅ Valid workspace name")

    registry_information = _get_registry_metadata_cached(deploy_module_registry_link)
    required_vars = extract_required_variables(registry_information)
    input_vars = []

    if len(required_vars) > 0:
        for variable in required_vars:
            var_name = variable["name"]
            if variable["sensitive"]:
                raw_value = deploy_form.text_input(var_name, type="password")
                input_vars.append(
                    {
                        "key": var_name,
                        "value": sanitize_variable_value(raw_value),
                        "category": "terraform",
                        "sensitive": True,
                    }
                )
            else:
                raw_value = deploy_form.text_input(var_name, type="default")
                input_vars.append(
                    {
                        "key": var_name,
                        "value": sanitize_variable_value(raw_value),
                        "category": "terraform",
                        "sensitive": False,
                    }
                )

    else:
        st.warning("No mandatory variables found")

    b_deploy = deploy_form.form_submit_button("Deploy", type="primary")

    if b_deploy:
        # Final validation before deployment
        is_valid, error_msg = validate_workspace_name(ws_name)
        if not is_valid:
            st.error(f"Cannot deploy: {error_msg}")
            return

        with st.spinner("Deploying workspace..."):
            st.write(no_code_id)
            payload = NoCodeDeploy(
                workspace_name=ws_name,
                workspace_description=f"{deploy_module_name} deployed from no-code portal",
                project_id=project["id"],
                vars=input_vars,
            ).generate()
            error = False
            deploy_result: Any
            try:
                deploy_result = api.no_code_provisioning.deploy(no_code_id, payload=payload)
            except Exception as ex:
                error_message = str(ex)
                if "already exists" in error_message.lower():
                    st.error(f"❌ Workspace '{ws_name}' already exists. Please choose a different name.")
                elif "unauthorized" in error_message.lower() or "forbidden" in error_message.lower():
                    st.error("❌ Permission denied. Check your API token has sufficient permissions.")
                else:
                    st.error(f"❌ Deployment failed: {error_message}")
                error = True

            if not error:
                st.success(
                    f"Workspace {ws_name} deployed [here]({api.get_url()}{deploy_result['data']['links']['self-html']})"
                )
                st.markdown(
                    f"Workspace {ws_name} deployed [here]({api.get_url()}{deploy_result['data']['links']['self-html']})"
                )


@st.cache_data(ttl=600)
def _get_registry_metadata_cached(registry_link: str) -> dict[str, Any]:
    """Cached registry metadata retrieval.

    Args:
        registry_link: Registry metadata API URL

    Returns:
        Module metadata including input variables
    """
    api: TFC = st.session_state[SessionKeys.API]
    return api._get(registry_link)  # type: ignore[no-any-return]


@st.cache_data
def extract_required_variables(registry_information: dict[str, Any]) -> list[dict[str, Any]]:
    required_vars = []
    for variable in registry_information["data"]["attributes"]["input-variables"]:
        if variable["required"]:
            required_vars.append(variable)
    return required_vars


def display_workspaces(project_id: str) -> None:
    workspaces = get_workspaces_by_project_id(project_id)
    st.dataframe(
        data=(ws for ws in workspaces),
        hide_index=True,
        column_order=["name", "tag-names", "source", "source-module-id", "no-code-upgrade-available", "self-html"],
        column_config={
            "name": st.column_config.TextColumn("Name", width="medium"),
            "self-html": st.column_config.LinkColumn("Link", display_text="Open Workspace", width="medium"),
            "no-code-upgrade-available": st.column_config.CheckboxColumn("Upgrade Available", width="small"),
        },
        width="stretch",
    )


def get_project_names() -> list[str]:
    return [project["attributes"]["name"] for project in st.session_state[SessionKeys.PROJECT_LIST]["data"]]


def get_project_by_name(name: str) -> dict[str, Any] | None:
    """Get project by name from cached project list."""
    project_list: dict[str, Any] = st.session_state[SessionKeys.PROJECT_LIST]
    for project in project_list["data"]:
        if project["attributes"]["name"] == name:
            return project  # type: ignore[no-any-return]

    return None


@st.cache_data(ttl=120, hash_funcs={"terrasnek.api.TFC": id})
def _get_workspaces_cached(url: str, token: str, org: str, project_id: str) -> list[dict[str, Any]]:
    """Cached workspace list retrieval.

    Args:
        url: HCP Terraform URL
        token: API token
        org: Organization name
        project_id: Project ID to filter workspaces

    Returns:
        List of workspaces with flattened attributes
    """
    api = create_tfc_client(token, url, org)
    if not api:
        return []

    workspaces = api.workspaces.list_all(filters=[{"keys": ["project", "id"], "value": project_id}])
    flat_workspaces = []
    for ws in workspaces["data"]:
        ws["attributes"]["id"] = ws["id"]
        ws["attributes"].update(ws["links"])
        flat_workspaces.append(ws["attributes"])

    for ws in flat_workspaces:
        ws["self-html"] = api.get_url() + ws["self-html"]

    return flat_workspaces


def get_workspaces_by_project_id(project_id: str) -> list[dict[str, Any]]:
    api: TFC = st.session_state[SessionKeys.API]
    url = api.get_url()
    org = str(api.get_org())  # Safe cast - API validated before this point
    token = str(api._token)  # Safe cast - API validated before this point

    return _get_workspaces_cached(url, token, org, project_id)


@st.cache_data(ttl=300)
def _get_organizations_cached(url: str, token: str) -> list[dict[str, Any]]:
    """Cached organization list retrieval.

    Args:
        url: HCP Terraform URL
        token: API token

    Returns:
        List of organizations
    """
    try:
        api = TFC(api_token=token, url=url)
        orgs_list = api.orgs.list()["data"]
        return orgs_list  # type: ignore[no-any-return]
    except Exception:
        return []


@st.cache_data(ttl=300)
def _get_projects_cached(url: str, token: str, org: str) -> dict[str, Any]:
    """Cached project list retrieval.

    Args:
        url: HCP Terraform URL
        token: API token
        org: Organization name

    Returns:
        Project list data
    """
    api = create_tfc_client(token, url, org)
    if not api:
        return {"data": []}
    return api.projects.list_all()  # type: ignore[no-any-return]


def settings() -> None:
    # Read persisted settings from query params
    saved_url = st.query_params.get(QueryParamKeys.URL, os.getenv(ENV_TFC_URL, DEFAULT_TFC_URL))
    saved_org = st.query_params.get(QueryParamKeys.ORG, None)

    with st.sidebar:
        # Wrap settings in form to prevent reruns during typing
        with st.form("settings_form", border=False):
            url = st.text_input("TFC URL", value=saved_url)

            # Automatically discover token from Terraform credentials
            discovered_token, token_source = get_terraform_token(url)
            default_token = discovered_token if discovered_token else ""

            # Display token source information outside form (doesn't trigger rerun)
            token = st.text_input(
                "TFC Token - https://app.terraform.io/app/settings/tokens",
                value=default_token,
                type="password",
                help="Token can be loaded from TF_TOKEN_* environment variable, ~/.terraform.d/credentials.tfrc.json, or entered manually",
            )

            token = token if token else ""  # Ensure token is not None

            # Fetch organizations using cached function
            orgs_list = _get_organizations_cached(url, token) if token else []
            org_names = [org["id"] for org in orgs_list]

            # Set default org from saved params if available
            default_org_index = 0
            if saved_org and saved_org in org_names:
                default_org_index = org_names.index(saved_org)

            org = st.selectbox("Organisation", org_names, index=default_org_index) if org_names else None

            b_config = st.form_submit_button("Apply configuration", type="primary", use_container_width=True)

        # Display info messages outside form
        if discovered_token:
            st.info(f"🔑 Token source: {token_source}")
        else:
            st.info("💡 No token found. Enter manually or configure Terraform credentials.")

        # Display error messages if org fetch failed
        if token and not orgs_list:
            st.error("❌ Invalid token or unable to connect to HCP Terraform")

        if b_config and org:
            # Persist settings to query params
            st.query_params[QueryParamKeys.URL] = url
            st.query_params[QueryParamKeys.ORG] = org

            api = create_tfc_client(token, url, org)
            st.session_state[SessionKeys.API] = api
            st.session_state[SessionKeys.MODULE_LIST] = get_link_list()
            st.session_state[SessionKeys.PROJECT_LIST] = _get_projects_cached(url, token, org)

        # Clear cache and refresh button (outside form)
        b_clear = st.button("Clear cache and refresh", use_container_width=True, type="secondary")
        if b_clear:
            # Clear Streamlit cache
            st.cache_data.clear()
            # Clear all session state
            for key in [SessionKeys.API, SessionKeys.MODULE_LIST, SessionKeys.PROJECT_LIST, SessionKeys.DEPLOY_MODULE]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()


def display() -> None:
    # Auto-initialize from query params if API not configured
    if SessionKeys.API not in st.session_state:
        saved_url = st.query_params.get(QueryParamKeys.URL)
        saved_org = st.query_params.get(QueryParamKeys.ORG)

        if saved_url and saved_org:
            # Attempt to restore configuration from saved params
            discovered_token, _ = get_terraform_token(saved_url)
            if discovered_token:
                try:
                    api = create_tfc_client(discovered_token, saved_url, saved_org)
                    st.session_state[SessionKeys.API] = api
                    st.session_state[SessionKeys.MODULE_LIST] = get_link_list()
                    st.session_state[SessionKeys.PROJECT_LIST] = _get_projects_cached(saved_url, discovered_token, saved_org)
                except Exception as e:
                    logging.debug(f"Failed to auto-initialize from query params: {e}")

    if SessionKeys.MODULE_LIST in st.session_state:
        logging.debug("using cached module list")
    else:
        st.error("Configure API and refresh to see modules")
        return

    st.title("Infrastructure Portal")

    all, deploy = st.tabs(["HCP Terraform Workflow", "Direct Module Deployment"])
    with all:
        display_list()
    with deploy:
        no_code_deploy()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s : %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])

    st.set_page_config(layout="wide")

    settings()
    display()
