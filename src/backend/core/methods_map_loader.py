"""
Methods map collector for payment and payout adapters.
"""

import importlib
import pkgutil
from functools import lru_cache
from typing import Any, Dict

from src.backend.core.logger import logger


@lru_cache(maxsize=1024)
def collect_metadata_maps(package_name: str, map_names: tuple[str, ...]) -> dict[str, Dict[str, Any]]:
    """
    Recursively scans all modules and sub-packages from package_name,
    collects dicts named in map_names into combined dicts.

    :param package_name: package name (e.g., 'src.schemas.adapters_dto')
    :param map_names: tuple of dictionary variable names to search for
    :return: dict where keys=map_name and values=combined dicts
    """
    collected_maps = {name: {} for name in map_names}
    visited_modules = set()

    def recursive_scan(pkg_name: str) -> None:
        """
        Recursively scans a package and its sub-packages, collecting dicts named in map_names.

        :param pkg_name: package name (e.g., 'src.schemas.adapters_dto')
        :return: None
        """
        if pkg_name in visited_modules:
            return  # Avoid cyclical repetition imports
        visited_modules.add(pkg_name)
        try:
            package = importlib.import_module(pkg_name)
        except Exception as e:
            logger.warning(f"Failed to import package {pkg_name}: {e}")
            return

        if not hasattr(package, "__path__"):
            # It's not a package, so it's a module, so we're trying to collect data from it
            scan_module(pkg_name, package)
            return

        # This is a package — let's go through all the modules and sub-packages inside
        for finder, modname, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            try:
                mod = importlib.import_module(modname)
                if ispkg:
                    # If it is a sub-packet, recursively scan it
                    recursive_scan(modname)
                else:
                    scan_module(modname, mod)
            except Exception as e:
                logger.warning(f"Failed to import module {modname}: {e}")

    def scan_module(modname: str, module) -> None:
        """
        Scans a module for dicts named in map_names.

        :param modname: module name (e.g., 'adapters_dto.payment_adapter')
        :param module: module object
        :return: None
        """
        logger.debug(f"Scanning module {modname}")
        for map_name in map_names:
            if hasattr(module, map_name):
                map_dict = getattr(module, map_name)
                if isinstance(map_dict, dict):
                    collected_maps[map_name].update(map_dict)
                    logger.debug(f"Collected {len(map_dict)} entries from {modname}.{map_name}")

    logger.debug(f"Starting scan of package {package_name} for maps {map_names}")
    recursive_scan(package_name)
    return collected_maps


METADATA_MAPS = collect_metadata_maps("src.schemas.adapters_dto", ("PAYMENT_METADATA_MAP", "PAYOUT_METADATA_MAP"))
