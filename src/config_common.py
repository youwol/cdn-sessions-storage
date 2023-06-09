import sys
from youwol.backends.cdn_sessions_storage import (
    Configuration as ServiceConfiguration,
    init_resources,
)
from youwol.utils.utils_paths import get_running_py_youwol_env

cache_prefix = "cdn_sessions_storage_"


async def get_py_youwol_env():
    py_youwol_port = sys.argv[2]
    if not py_youwol_port:
        raise RuntimeError(
            "The configuration requires py-youwol to run on port provided as command line option"
        )
    return await get_running_py_youwol_env(py_youwol_port)
