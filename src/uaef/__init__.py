"""
Universal Autonomous Enterprise Fabric (UAEF)

An enterprise platform for coordinating autonomous agents,
validating workflow integrity through a permissioned trust ledger,
and automating financial settlements tied to operational outcomes.
"""

__version__ = "0.1.0"

from uaef.core import (
    Settings,
    configure_logging,
    get_logger,
    get_session,
    get_settings,
    init_db,
)

__all__ = [
    "__version__",
    "Settings",
    "get_settings",
    "configure_logging",
    "get_logger",
    "get_session",
    "init_db",
]
