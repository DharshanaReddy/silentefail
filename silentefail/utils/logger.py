import logging

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"silentefail.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[silentefail] %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    return logger
