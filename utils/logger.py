import logging
import traceback
from functools import wraps

# Configure the logger
logger = logging.getLogger('coachmeplay')
logger.setLevel(logging.INFO)

# Create handlers
handler = logging.FileHandler('logs/app.log')
handler.setLevel(logging.INFO)

# Create formatters and add it to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(handler)

def log_exception(func):
    """Decorator to log full exception tracebacks"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Exception in {func.__name__}: {str(e)}\nTraceback:\n{traceback.format_exc()}")
            raise
    return wrapper