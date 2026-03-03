"""
Adapter loader for FastAPI adapters.

This function loads all Payment gateway adapters from a given folder and registers them in the application's state.
"""

import importlib
import pkgutil

from fastapi import FastAPI

from src.core.logger import AppLogger


def auto_register_adapters(
    app: FastAPI,
    adapter_path: str = "adapters",
    *,
    logger: AppLogger,
):
    """
    Automatically include FastAPI adapters to state attr from given folder.

    :param app: The FastAPI application.
    :param adapter_path: The path to the adapters.
    :param logger: The logger instance to use for logging.
    :return: None
    """
    app.state.adapters = {}  # Initialize adapters state attribute
    for finder, name, ispkg in pkgutil.iter_modules([adapter_path]):
        if name != "meta":
            logger.debug(f"Looking for plugins in {adapter_path}/{name}")
            adapter_path = adapter_path.replace("/", ".")
            module_name = f"{adapter_path}.{name}"
            logger.debug(f"Module name: {module_name}")
            try:
                mod = importlib.import_module(module_name)
                logger.debug(f"Imported: {mod}")
                if hasattr(mod, "PaymentGateway"):
                    app.state.adapters[name] = mod.PaymentGateway
                    logger.info(f"Registered adapter: /{name}/* from {module_name}")
                else:
                    logger.warning(f"No adapter found in {module_name}")
            except ModuleNotFoundError as e:
                logger.warning(f"No adapters found for {name}: {e}")
