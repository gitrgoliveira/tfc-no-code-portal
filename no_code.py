import json

# Example usage
# vars = [
#     {'key': 'region', 'value': 'eu-central-1', 'category': 'terraform'},
#     {'key': 'ami', 'value': 'ami‑077062', 'category': 'terraform'}
# ]
# generator = PayloadGenerator('no-code-workspace', 'A workspace to enable the No-Code provisioning workflow.', 'prj-yuEN6sJVra5t6XVy', vars)
# print(generator.generate())

class NoCodeDeploy:
    def __init__(self, workspace_name, workspace_description, project_id, vars):
        self.workspace_name = workspace_name
        self.workspace_description = workspace_description
        self.project_id = project_id
        self.vars = vars
        
    def generate(self):
        payload = {
            "data": {
                "type": "workspaces",
                "attributes": {
                    "name": self.workspace_name,
                    "description": self.workspace_description,
                },
                "relationships": {
                    "project": {
                        "data": {
                            "id": self.project_id,
                            "type": "project"
                        }
                    },
                    "vars": {
                        "data": []
                    }
                }
            }
        }
        
        for var in self.vars:
            payload["data"]["relationships"]["vars"]["data"].append({
                "type": "vars",
                "attributes": {
                    "key": var['key'],
                    "value": var['value'],
                    "category": var['category'],
                    "hcl": True,
                    "sensitive": False
                }
            })
        
        return payload


