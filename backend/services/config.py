import os

# Define supported models and their configurations
SUPPORTED_MODELS = {
    "claude-3-haiku": {
        "id": "anthropic.claude-3-haiku-20240307-v1:0",
        "config": {
            "temperature": 0.5,
            "topP": 0.9,
            "maxTokens": 1000
        }
    },
    "claude-3-5-haiku": {
        "id": "anthropic.claude-3-5-haiku-20241022-v1:0",
        "config": {
            "temperature": 0.5,
            "topP": 0.9,
            "maxTokens": 1000
        }
    }
}

# Logging configurations
LOG_DIR = os.path.dirname(__file__)
APP_LOG_FILE = os.path.join(LOG_DIR, 'app.log')
EXECUTION_TIMES_LOG_FILE = os.path.join(LOG_DIR, 'execution_times.log')

# AWS Configurations
DEFAULT_AWS_REGION = "us-west-2"
METADATA_SERVICE_URL = "http://169.254.169.254/latest"
