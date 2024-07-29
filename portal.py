import logging
import os
import string
from urllib.parse import urljoin
import random
import string
import streamlit as st
from terrasnek.api import TFC
from no_code import NoCodeDeploy
from typing import Any
# from typing import list
## get terraform URL and credentials from environment

TFC_TOKEN = os.getenv("TFC_TOKEN", None)

NUM_COLUMNS = 4


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
            
            no_code_list.append({ 'name': attr['name'], 'link': link, 'data': no_code_module })
            
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

    s_project = st.selectbox("Target Project", get_project_names())
    
    st.markdown("## Infrastructure to deploy")
    cols = st.columns(NUM_COLUMNS)
    for i, module in enumerate(st.session_state['module_list']):
        col = cols[i % NUM_COLUMNS]
        if col.button(label=module['name'],use_container_width=True,type='primary'):
            st.session_state['deploy_module'] = (module['name'], module['data'])

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
    (deploy_module_name, deploy_module_data) = st.session_state['deploy_module']
    no_code_id = deploy_module_data['data']['id']

    deploy_form.markdown(f"## Deploy {deploy_module_name}")
    random_chars = ''.join(random.choice(string.ascii_letters) for _ in range(3))
    
    ws_name = deploy_form.text_input("Workspace name", value=f"{deploy_module_name}-{random_chars}")
    # nocode_options = show_with_options(api, no_code_id)
    
    vars = {}
    if 'included' in deploy_module_data:
        for variable in deploy_module_data['included']:
            var_name = variable['attributes']['variable-name']
            # deploy_form.json(variable['attributes'])
            vars[var_name] = deploy_form.text_input(var_name)
                
        # deploy_form.json(deploy_module_data, expanded=False)
    else:
        st.warning("No variables found")
        deploy_form.json(deploy_module_data, expanded=False)

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
                                            vars=[]).generate()
            st.json(payload)
            error = False
            deploy_result : Any
            try:    
                deploy_result = api.no_code_provisioning.deploy(no_code_id, payload=payload)
            except Exception as ex:
                st.error(ex)
                error = True
                        
            if not error:
                st.success(f"Workspace {ws_name} deployed [here]({deploy_result['data']['links']['self-html']})")
                st.markdown(f"Workspace {ws_name} deployed [here]({deploy_result['data']['links']['self-html']})")
                st.write(deploy_result)
    # if b_clear:
    #     st.session_state['deploy_module'] = None
    #     del st.session_state['deploy_module']
                    

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
    TFC_URL = os.getenv("TFC/E_URL", "https://app.terraform.io")
    with st.sidebar:    
        url = st.text_input("TFC URL", value=TFC_URL)
        token = st.text_input("TFC Token", value=TFC_TOKEN, type="password")
        try:
            api = TFC(api_token=token, url=url)
            # api = TFC(api_token=token, url=url,log_level=logging.DEBUG)
            orgs_list = api.orgs.list()['data']
            org_names = [org['id'] for org in orgs_list]
            org = st.selectbox("Organisation", org_names)
        except:
            st.error("Invalid token or URL")

        b_config = st.button("Configure / Refresh", use_container_width=True)
        
        if b_config:
            api = TFC(api_token=token, url=url)
            api.set_org(org)
            st.session_state['api'] = api
            st.session_state['module_list'] = get_link_list()
            st.session_state['project_list'] = api.projects.list_all()
            
def display ():

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
    