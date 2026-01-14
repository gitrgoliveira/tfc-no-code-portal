import logging
import os
import json
import platform
from pathlib import Path
from urllib.parse import urljoin, urlparse

import streamlit as st
from terrasnek.api import TFC
from no_code import NoCodeDeploy
from typing import Any, Tuple, Optional
# from typing import list
## get terraform URL and credentials from environment

TFC_TOKEN = os.getenv("TFC_TOKEN", None)

NUM_COLUMNS = 4


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


def extract_hostname(url: str) -> str:
    """Extract hostname from URL for credential lookup.
    
    Args:
        url: Full URL (e.g., 'https://app.terraform.io')
        
    Returns:
        Hostname without protocol (e.g., 'app.terraform.io')
    """
    parsed = urlparse(url)
    hostname = parsed.netloc if parsed.netloc else parsed.path.split('/')[0]
    # Remove port if present
    if ':' in hostname:
        hostname = hostname.split(':')[0]
    return hostname.lower().strip('/')


def get_terraform_token(url: str = "https://app.terraform.io") -> Tuple[Optional[str], str]:
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
    env_var_name = f"TF_TOKEN_{hostname.replace('.', '_').replace('-', '__')}"
    token = os.getenv(env_var_name)
    if token and token.strip():
        logging.debug(f"Token loaded from environment variable: {env_var_name}")
        return token.strip(), f"Environment Variable ({env_var_name})"
    
    # Try credentials file
    creds_file = get_credentials_file_path()
    if creds_file.exists():
        try:
            with open(creds_file, 'r') as f:
                data = json.load(f)
                credentials = data.get('credentials', {})
                host_creds = credentials.get(hostname, {})
                token = host_creds.get('token')
                if token and token.strip():
                    logging.debug(f"Token loaded from credentials file for hostname: {hostname}")
                    return token.strip(), f"Credentials File ({creds_file})"
        except json.JSONDecodeError as e:
            logging.warning(f"Invalid JSON in credentials file {creds_file}: {e}")
        except PermissionError as e:
            logging.warning(f"Permission denied reading credentials file {creds_file}: {e}")
        except Exception as e:
            logging.warning(f"Error reading credentials file {creds_file}: {e}")
    else:
        logging.debug(f"Credentials file not found: {creds_file}")
    
    # Fallback to legacy environment variable
    token = os.getenv("TFC_TOKEN")
    if token and token.strip():
        logging.debug("Token loaded from legacy TFC_TOKEN environment variable")
        return token.strip(), "Environment Variable (TFC_TOKEN)"
    
    logging.debug("No token found from any source")
    return None, "Not Found (Manual Entry Required)"


# def get_no_code_modules():
#     api: TFC  = st.session_state['api']
#     result = []
#     module_list = api.registry_modules.list_all()['data']
#     print (module_list)
    
def get_link_list():
    if not st.session_state.get('api', False):
        logging.error("no api configured")
        return []
    
    api: TFC  = st.session_state['api']
    no_code_list = []
    ## get all the modules from Terraform Cloud
    module_list = api.registry_modules.list_all()
    hostname = api.get_hostname()
    organization = api.get_org()
    for module in module_list['data']:
        ## filter by which ones are marked as no code
        if module['attributes']['no-code']:
            attr = module['attributes']
            latest_version = ""
            registry_origin = "private"
            no_code_module_id = module['relationships']['no-code-modules']['data'][0]['id']
            no_code_module = show_with_options(api, no_code_module_id)
            if len(attr['version-statuses']) == 0:
                logging.warning(f"No version detected. May be a public module:\n {module}")
                logging.warning(no_code_module)
                registry_origin = "public"
                latest_version = no_code_module['data']['attributes']['version-pin']              
            else:
                latest_version = attr['version-statuses'][0]['version']
            # example link
            # https://app.terraform.io/app/hc-ric-demo/registry/modules/private/hc-ric-demo/k8s/aws/1.0.3/new-workspace
            link = f"https://{hostname}/app/{organization}/registry/modules/{registry_origin}/{attr['namespace']}/{attr['name']}/{attr['provider']}/{latest_version}/new-workspace"
            # registry_link = f"https://{hostname}/api/registry/v1/modules/{organization}/{attr['name']}/{attr['provider']}/{latest_version}"
            registry_link = f"https://{hostname}/api/registry/{registry_origin}/v2/modules/{attr['namespace']}/{attr['name']}/{attr['provider']}/metadata/{latest_version}?organization_name={organization}"
            no_code_list.append({'name': attr['name'], 'link': link, 'data': no_code_module , 'registry_link': registry_link})
            
    return no_code_list


def display_list():
    st.markdown("_Start a no code module workflow with HCP Terraform_",)
    cols = st.columns(NUM_COLUMNS)
    for i, module in enumerate(st.session_state['module_list']):
        col = cols[i % NUM_COLUMNS]
        col.link_button(label=module['name'], url=module['link'],use_container_width=True,type='primary')
        
def no_code_deploy():
    
    if not st.session_state.get('api', False):
        st.warning("no api configured")
        return

    # Get project names and check for saved selection
    project_names = get_project_names()
    saved_project = st.query_params.get('project')
    default_project_index = 0
    if saved_project and saved_project in project_names:
        default_project_index = project_names.index(saved_project)
    
    s_project = st.selectbox("Target Project", project_names, index=default_project_index, key="project_select")
    
    # Persist project selection to query params
    if s_project:
        st.query_params['project'] = s_project
    
    st.markdown("## Infrastructure to deploy")
    cols = st.columns(NUM_COLUMNS)
    for i, module in enumerate(st.session_state['module_list']):
        col = cols[i % NUM_COLUMNS]
        if col.button(label=module['name'],use_container_width=True,type='primary'):
            st.session_state['deploy_module'] = (module['name'], module['data'], module['registry_link'])

        # b_deploy[module['name']] = col.button(label=module['name'],use_container_width=True,type='primary')
        # col.link_button(label=module['name'], url=module['link'],use_container_width=True,type='primary')
    
    st.divider()
    if s_project:
        st.markdown("## Current infrastructure")
        project = get_project_by_name(s_project)
        if project != None:
            st.write(project['attributes'].get('description', "no project description"))
            # st.write(api.projects.show(project['id']))
            display_workspaces(project['id'])
            if 'deploy_module' in st.session_state:          
                deploy_nocode_module(project)

def show_with_options(api: TFC, module_id: str):
    url = f"{api.no_code_provisioning._no_code_base_url}/{module_id}"
    return api.no_code_provisioning._show(url=url, include=['variable_options'])

def deploy_nocode_module(project):

    deploy_form = st.form(key="deploy_form", border=True)
    api: TFC  = st.session_state['api']
    (deploy_module_name, deploy_module_data, deploy_module_registry_link) = st.session_state['deploy_module']
    no_code_id = deploy_module_data['data']['id']

    deploy_form.markdown(f"## Deploy {deploy_module_name}")
    # random_chars = ''.join(random.choice(string.ascii_letters) for _ in range(3))
    
    ws_name = deploy_form.text_input("Workspace name", key="ws_name",value=f"{deploy_module_name}-")
    nocode_options = show_with_options(api, no_code_id)
    
    # deploy_form.json(deploy_module_data, expanded=False)
    # deploy_form.json(nocode_options, expanded=False)
    
    registry_information = api._get(deploy_module_registry_link)
    required_vars = extract_required_variables (registry_information)
    # deploy_form.json(registry_information,expanded=False)
    # deploy_form.json(required_vars, expanded=False)
    input_vars = []
    
    if len(required_vars) > 0:
        for variable in required_vars:
            var_name = variable['name']
            if variable['sensitive']:
                input_vars.append({
                    "key": var_name,
                    "value": deploy_form.text_input(var_name, type='password'),
                    "category": "terraform",
                    "sensitive": True
                })
            else:
                input_vars.append({
                    "key": var_name,
                    "value": deploy_form.text_input(var_name, type='default'),
                    "category": "terraform",
                    "sensitive": False
                })
                
    else:
        st.warning("No mandatory variables found")
    # if 'included' in nocode_options:
    #     for variable in nocode_options['included']:
    #         var_name = variable['attributes']['variable-name']
    #         # deploy_form.json(variable['attributes'])
    #         # vars[var_name] = 
            
    #         input_vars.append({
    #             "key": var_name,
    #             "value": deploy_form.text_input(var_name),
    #             "category": "terraform"
    #         })
                
    # else:
    #     st.warning("No variables found")
    #     deploy_form.json(deploy_module_data, expanded=False)
    #     deploy_form.json(nocode_options, expanded=False)

    b_deploy = deploy_form.form_submit_button("Deploy", type="primary")
    # col1, col2 = st.columns(2)
    # with col1:
    #     b_deploy = st.button("Deploy", type="primary")
    # with col2:
    #     b_clear = st.button("Clear")
                    
    if b_deploy:
        with st.spinner():
                        # Extract the stored values from session state
                        # st.write(deploy_module_data)
            st.write(no_code_id)
            payload = NoCodeDeploy(workspace_name=ws_name,
                                            workspace_description=f"{deploy_module_name} deployed from no-code portal",
                                            project_id=project['id'],
                                            vars=input_vars).generate()
            # st.json(payload)
            error = False
            deploy_result : Any
            try:    
                deploy_result = api.no_code_provisioning.deploy(no_code_id, payload=payload)
            except Exception as ex:
                st.error(ex)
                error = True
                        
            if not error:
                st.success(f"Workspace {ws_name} deployed [here]({api.get_url()}{deploy_result['data']['links']['self-html']})")
                st.markdown(f"Workspace {ws_name} deployed [here]({api.get_url()}{deploy_result['data']['links']['self-html']})")
                # st.write(deploy_result)
    # if b_clear:
    #     st.session_state['deploy_module'] = None
    #     del st.session_state['deploy_module']
                    
def extract_required_variables (registry_information):
    required_vars = []
    for variable in registry_information['data']['attributes']['input-variables']:
        if variable['required']:
            required_vars.append(variable)
    # for variable in registry_information['root']['inputs']:
    #     if variable['required']:
    #         required_vars.append(variable)
    #         print (variable)
    return required_vars

def display_workspaces(project_id):
    workspaces = get_workspaces_by_project_id(project_id)
    st.dataframe(data=(ws for ws in workspaces),
                         hide_index=True,
                         column_order=["name", "tag-names",
                                       "source",
                                    #    "source-name",
                                    #    "source-url", 
                                       "source-module-id",
                                       "no-code-upgrade-available",
                                       "self-html"],
                         column_config={
                             "name": st.column_config.TextColumn("Name", width="medium"),
                             "self-html": st.column_config.LinkColumn("Link", display_text="Open Workspace",width="medium"),
                             "no-code-upgrade-available": st.column_config.CheckboxColumn("Upgrade Available",width="small")
                         },use_container_width=True
                         )      
    
    
def get_project_names():
    return [project['attributes']['name'] for project in st.session_state['project_list']['data']]

def get_project_by_name(name):
    for project in st.session_state['project_list']['data']:
        if project['attributes']['name'] == name:
            return project
    
    return None

def get_workspaces_by_project_id(project_id):
    api: TFC  = st.session_state['api']
    
    workspaces = api.workspaces.list_all(filters=[{
                "keys": ['project', 'id'],
                'value': project_id
            }])
    flat_workspaces = []
    for ws in workspaces['data']:
        ws['attributes']['id'] = ws['id']

        ws['attributes'].update(ws['links'])
        flat_workspaces.append(ws['attributes'])
        
    for ws in flat_workspaces:
        ws['self-html'] = api.get_url() + ws['self-html']
        
    return flat_workspaces

def settings():
    # Read persisted settings from query params
    saved_url = st.query_params.get('url', os.getenv("TFC/E_URL", "https://app.terraform.io"))
    saved_org = st.query_params.get('org', None)
    
    with st.sidebar:    
        url = st.text_input("TFC URL", value=saved_url)
        
        # Automatically discover token from Terraform credentials
        discovered_token, token_source = get_terraform_token(url)
        default_token = discovered_token if discovered_token else ""
        
        # Display token source information
        if discovered_token:
            st.info(f"🔑 Token source: {token_source}")
        else:
            st.info("💡 No token found. Enter manually or configure Terraform credentials.")
        
        token = st.text_input(
            "TFC Token - https://app.terraform.io/app/settings/tokens",
            value=default_token,
            type="password",
            help="Token can be loaded from TF_TOKEN_* environment variable, ~/.terraform.d/credentials.tfrc.json, or entered manually"
        )
        
        try:
            api = TFC(api_token=token, url=url)
            # api = TFC(api_token=token, url=url,log_level=logging.DEBUG)
            orgs_list = api.orgs.list()['data']
            org_names = [org['id'] for org in orgs_list]
            
            # Set default org from saved params if available
            default_org_index = 0
            if saved_org and saved_org in org_names:
                default_org_index = org_names.index(saved_org)
            
            org = st.selectbox("Organisation", org_names, index=default_org_index)
        except Exception as e:
            st.error(f"Invalid token or URL: {str(e)}")
            org = None

        b_config = st.button("Apply configuration", use_container_width=True, type="primary")
        
        if b_config and org:
            # Persist settings to query params
            st.query_params['url'] = url
            st.query_params['org'] = org
            
            api = TFC(api_token=token, url=url)
            api.set_org(org)
            st.session_state['api'] = api
            st.session_state['module_list'] = get_link_list()
            st.session_state['project_list'] = api.projects.list_all()
        
        # Clear cache and refresh button
        b_clear = st.button("Clear cache and refresh", use_container_width=True, type="secondary")
        if b_clear:
            # Clear all session state
            for key in ['api', 'module_list', 'project_list', 'deploy_module']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
            
def display ():
    # Auto-initialize from query params if API not configured
    if 'api' not in st.session_state:
        saved_url = st.query_params.get('url')
        saved_org = st.query_params.get('org')
        
        if saved_url and saved_org:
            # Attempt to restore configuration from saved params
            discovered_token, _ = get_terraform_token(saved_url)
            if discovered_token:
                try:
                    api = TFC(api_token=discovered_token, url=saved_url)
                    api.set_org(saved_org)
                    st.session_state['api'] = api
                    st.session_state['module_list'] = get_link_list()
                    st.session_state['project_list'] = api.projects.list_all()
                except Exception:
                    pass  # Silently fail, user will need to reconfigure

    if 'module_list' in st.session_state:
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
        format='%(asctime)s [%(levelname)s] %(name)s : %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
    
    st.set_page_config(layout="wide")

    settings()    
    display()
    