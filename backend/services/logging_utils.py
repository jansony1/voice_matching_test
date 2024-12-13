import logging
import os
from datetime import datetime
from .config import APP_LOG_FILE, EXECUTION_TIMES_LOG_FILE

def ensure_log_directory():
    """
    Ensure the log directory exists and is writable
    """
    log_dir = os.path.dirname(APP_LOG_FILE)
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
            logging.info(f"Created log directory: {log_dir}")
        except Exception as e:
            print(f"Error creating log directory: {e}")
            return False
    
    # Check if directory is writable
    if not os.access(log_dir, os.W_OK):
        print(f"Log directory is not writable: {log_dir}")
        return False
    
    return True

def setup_logging():
    """
    Configure logging for the application
    """
    # Ensure log directory exists and is writable
    if not ensure_log_directory():
        print("Failed to setup logging due to directory issues")
        return

    try:
        # Main application logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s: %(message)s',
            handlers=[
                logging.FileHandler(APP_LOG_FILE),
                logging.StreamHandler()
            ]
        )
        
        # Create a dedicated logger for execution times
        execution_logger = logging.getLogger('execution_times')
        execution_logger.setLevel(logging.INFO)
        
        # Remove any existing handlers to prevent duplicate logging
        execution_logger.handlers = []
        
        # Add file handler for execution times
        execution_file_handler = logging.FileHandler(EXECUTION_TIMES_LOG_FILE)
        execution_file_handler.setFormatter(logging.Formatter('%(message)s'))
        execution_logger.addHandler(execution_file_handler)
        execution_logger.propagate = False  # Prevent log propagation to root logger
        
        logging.info("Logging setup completed successfully")
        
    except Exception as e:
        print(f"Error setting up logging: {e}")

def log_execution_time(model_id, execution_time):
    """
    Log the execution time of Bedrock API calls
    
    :param model_id: Identifier of the model used
    :param execution_time: Time taken for execution
    """
    try:
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp},{model_id},{execution_time:.4f}"
        
        # Get the dedicated execution times logger
        execution_logger = logging.getLogger('execution_times')
        
        # Log to execution times file
        execution_logger.info(log_entry)
        
        # Log to main application log
        logging.info(f"Logged execution time for model {model_id}: {execution_time:.4f} seconds")
    except Exception as e:
        logging.error(f"Failed to log execution time: {e}")
        print(f"Error logging execution time: {e}")  # Fallback console output
