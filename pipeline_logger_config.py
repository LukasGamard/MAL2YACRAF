import logging

def setup_logging():
    # Only configure the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)  # Set the root logger's level to WARNING

    # Create a console handler with WARNING level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)

    # Create a simple formatter and attach it to the handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Add the handler to the logger (root logger in this case)
    logger.addHandler(console_handler)