"""
Main function to initialize the FastAPI application.
"""

# Importing the necessary modules and logger initialization before the rest of importing.
# This will ensure that all necessary modules and logger are initialized before the application is started.
from src.core.logger.logger_factory import setup_logger

setup_logger()

from src.app.setup import create_app

app = create_app()
