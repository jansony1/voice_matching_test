import os
import json

# In Docker environment, the config file is mounted at /app/shared/config/models_config.json
MODELS_CONFIG_PATH = '/app/shared/config/models_config.json'

# Load models configuration from the shared JSON file
def load_models_config():
    try:
        with open(MODELS_CONFIG_PATH, 'r') as f:
            config = json.load(f)
            return config.get('supported_models', {})
    except FileNotFoundError:
        print(f"Warning: Models configuration file not found at {MODELS_CONFIG_PATH}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in models configuration file at {MODELS_CONFIG_PATH}")
        return {}

# Define supported models dynamically from the configuration file
SUPPORTED_MODELS = load_models_config()

# Logging configurations
LOG_DIR = os.path.dirname(os.path.dirname(__file__))
APP_LOG_FILE = os.path.join(LOG_DIR, 'app.log')
EXECUTION_TIMES_LOG_FILE = os.path.join(LOG_DIR, 'execution_times.log')

# AWS Configurations
DEFAULT_AWS_REGION = "us-west-2"
METADATA_SERVICE_URL = "http://169.254.169.254/latest"
