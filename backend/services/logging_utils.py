import logging
import os
from datetime import datetime
from .config import APP_LOG_FILE, EXECUTION_TIMES_LOG_FILE

# Create a dedicated logger for execution times to prevent duplicate logging
execution_logger = logging.getLogger('execution_times')
execution_logger.setLevel(logging.INFO)
execution_file_handler = logging.FileHandler(EXECUTION_TIMES_LOG_FILE)
execution_file_handler.setFormatter(logging.Formatter('%(message)s'))
execution_logger.addHandler(execution_file_handler)
execution_logger.propagate = False  # Prevent log propagation to root logger

def setup_logging():
    """
    Configure logging for the application
    """
    # Main application logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(APP_LOG_FILE),
            logging.StreamHandler()
        ]
    )

def log_execution_time(model_id, execution_time):
    """
    Log the execution time of Bedrock API calls
    
    :param model_id: Identifier of the model used
    :param execution_time: Time taken for execution
    """
    try:
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp},{model_id},{execution_time:.4f}"
        
        # Use the dedicated execution times logger
        execution_logger.info(log_entry)
        
        # Optional: log to main application log
        logging.info(f"Logged execution time for model {model_id}: {execution_time:.4f} seconds")
    except Exception as e:
        logging.error(f"Failed to log execution time: {e}")
