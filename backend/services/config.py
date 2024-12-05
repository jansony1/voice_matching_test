import os
import json
import logging

def get_models_config_path():
    """
    Get the path to models_config.json, handling both Docker and local environments
    """
    # Docker environment path (when using volume mount)
    docker_path = '/app/shared/config/models_config.json'
    
    # Local development path
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                             'shared', 'config', 'models_config.json')
    
    # Try Docker path first (volume mounted path)
    if os.path.exists(docker_path):
        logging.info(f"Using Docker volume mounted config path: {docker_path}")
        return docker_path
    
    # Fallback to local path
    if os.path.exists(local_path):
        logging.info(f"Using local development config path: {local_path}")
        return local_path
    
    logging.error("Could not find models_config.json in any location")
    logging.error(f"Tried Docker path: {docker_path}")
    logging.error(f"Tried local path: {local_path}")
    return None

# Load models configuration from the shared JSON file
def load_models_config():
    try:
        config_path = get_models_config_path()
        if not config_path:
            logging.error("No valid config path found")
            return {}

        logging.info(f"Loading models config from: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
            # Log the loaded configuration
            logging.info("Successfully loaded models configuration:")
            logging.info(json.dumps(config, indent=2))
            supported_models = config.get('supported_models', {})
            if not supported_models:
                logging.warning("No supported_models found in config file")
            return supported_models
    except FileNotFoundError:
        logging.error(f"Models configuration file not found")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in models configuration file: {str(e)}")
        return {}
    except Exception as e:
        logging.error(f"Unexpected error loading models config: {str(e)}")
        return {}

# Define supported models dynamically from the configuration file
SUPPORTED_MODELS = load_models_config()

# Log the final SUPPORTED_MODELS value
logging.info("=== FINAL SUPPORTED_MODELS CONFIGURATION ===")
logging.info(json.dumps(SUPPORTED_MODELS, indent=2))
logging.info("==========================================")

# Logging configurations
LOG_DIR = os.path.dirname(os.path.dirname(__file__))
APP_LOG_FILE = os.path.join(LOG_DIR, 'app.log')
EXECUTION_TIMES_LOG_FILE = os.path.join(LOG_DIR, 'execution_times.log')

# AWS Configurations
DEFAULT_AWS_REGION = "us-west-2"
METADATA_SERVICE_URL = "http://169.254.169.254/latest"
