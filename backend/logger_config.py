import logging

def setup_logging():
    """Configure logging for the application"""
    # Configure basic logging
    logging.basicConfig(
        level=logging.ERROR,  # Set global level to ERROR
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    # Silence all third-party loggers
    SILENT_LOGGERS = [
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "sqlalchemy.orm",
        "httpx",
        "github",
        "urllib3",
        "huggingface_hub",
        "transformers",
        "sentence_transformers",
        "embeddings",
        "torch",
        "tqdm"
    ]

    for logger_name in SILENT_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)
        logging.getLogger(logger_name).propagate = False

    # Create our app's logger
    logger = logging.getLogger("solodit_checklist")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Create a console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    return logger 