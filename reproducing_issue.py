# Reproducing script that uses the actual port_ocean config classes and mimics Helm input
from port_ocean.config.settings import IntegrationConfiguration
from port_ocean.context.ocean import PortOceanContext
from pydantic import ValidationError

# Simulate the config as loaded from Helm values (camelCase)
config_from_helm = {
    'jiraHost': 'https://example.atlassian.net',
    'atlassianUserEmail': 'user@example.com',
    'atlassianUserToken': 'token123',
}

# Simulate the port config as loaded from Helm values (camelCase)
port_config_from_helm = {
    'clientId': 'id',
    'clientSecret': 'secret',
    'baseUrl': 'https://api.getport.io',
}

# Build a config dict as IntegrationConfiguration expects, but with camelCase keys
config_dict = {
    'integration': {
        'config': config_from_helm,
        'type': 'jira',
        'identifier': 'jira',
    },
    'port': port_config_from_helm,
}

try:
    cfg = IntegrationConfiguration(**config_dict)
    # Setup app and context
    class FakeApp:
        def __init__(self, config):
            self.config = config
    fake_app = FakeApp(cfg)
    context = PortOceanContext(fake_app)
    # Try accessing snake_case keys as in integration
    jira_host = context.integration_config['jira_host']
    atlassian_user_email = context.integration_config['atlassian_user_email']
    atlassian_user_token = context.integration_config['atlassian_user_token']
    print('Issue Resolved')
except KeyError as e:
    print(f'Issue Reproduced: Missing key {e}')
except ValidationError as e:
    print(f'Issue Reproduced: Validation error:\n{e}')
except Exception as e:
    print(f'Issue Reproduced: {e}')
