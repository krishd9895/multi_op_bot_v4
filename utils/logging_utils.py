# utils/logging_utils.py
"""
Logging configuration for the application
"""
import logging

def setup_logging():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    return logger
