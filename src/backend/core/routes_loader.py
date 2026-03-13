"""
Routes registration function to automatically include FastAPI routers from directory.
"""

import importlib
import pkgutil

from fastapi import FastAPI

from src.backend.core.logger import AppLogger


def auto_register_routes(
    app: FastAPI,
    plugin_path: str = "plugins",
    prefix: str = "",
    *,
    logger: AppLogger,
):
    """
    Automatically include FastAPI routers from given folder.

    :param app: The FastAPI application.
    :param plugin_path: The path to the routers.
    :param prefix: The prefix for the router.
    :param logger: The logger instance to use for logging.
    :return: None
    """
    for finder, name, ispkg in pkgutil.iter_modules([plugin_path]):
        logger.debug(f"Looking for routers in {plugin_path}/{name}")
        plugin_path = plugin_path.replace("/", ".")
        module_name = f"{plugin_path}.{name}.routes"
        logger.debug(f"Module name: {module_name}")
        try:
            mod = importlib.import_module(module_name)
            logger.debug(f"Imported: {mod}")
            if hasattr(mod, "router"):
                if name not in ("maintenance", "base"):
                    router_prefix = prefix + "/" + name
                else:
                    router_prefix = prefix
                app.include_router(mod.router, prefix=router_prefix)
                logger.info(f"Registered router: /{name}/* from {module_name}")
            else:
                logger.warning(f"No router found in {module_name}")
        except ModuleNotFoundError as e:
            logger.warning(f"No routes found for {name}: {e}")
