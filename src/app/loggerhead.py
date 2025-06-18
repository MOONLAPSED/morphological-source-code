import logging
import datetime
from logging import Formatter, StreamHandler

# Configure logger
logger = logging.getLogger("SmartIntrospection")
logger.setLevel(logging.DEBUG)

# Define a custom formatter
class CustomFormatter(Formatter):
    def format(self, record):
        # Base format
        timestamp = datetime.datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        level = f"{record.levelname:<8}"
        message = record.getMessage()
        source = f"({record.filename}:{record.lineno})"
        # Color codes for terminal output (if needed)
        color_map = {
            'INFO': "\033[32m",     # Green
            'WARNING': "\033[33m",  # Yellow
            'ERROR': "\033[31m",    # Red
            'CRITICAL': "\033[41m", # Red background
            'DEBUG': "\033[34m",    # Blue
        }
        reset = "\033[0m"
        colored_level = f"{color_map.get(record.levelname, '')}{level}{reset}"
        return f"{timestamp} - {colored_level} - {message} {source}"

# Add handler with custom formatter
handler = StreamHandler()
handler.setFormatter(CustomFormatter())
logger.addHandler(handler)

# Example of improved logging calls
def log_module_info(module_name, metadata, runtime_info, exports):
    logger.info(f"Module '{module_name}' metadata captured.")
    logger.debug(f"Metadata details: {metadata}")
    logger.info(f"Module '{module_name}' runtime info: {runtime_info}")
    if exports:
        logger.info(f"Module '{module_name}' exports: {exports}")

# Example logging
log_module_info(
    "example_module",
    {"author": "John Doe", "version": "1.0.0"},
    {"type": "module", "import_time": datetime.datetime.now()},
    ["function_one", "function_two"],
)
logger.error("Query validation failed: Access denied to variable 'x'")
logger.critical("CRITICAL")