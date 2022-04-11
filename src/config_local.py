from pathlib import Path

from config_common import get_py_youwol_env, on_before_startup

from youwol_cdn_sessions_storage import Constants, Configuration

from youwol_utils import LocalStorageClient
from youwol_utils.context import ConsoleContextLogger
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware
from youwol_utils.servers.fast_api import FastApiMiddleware, ServerOptions, AppConfiguration


async def get_configuration():

    env = await get_py_youwol_env()
    databases_path = Path(env['pathsBook']['databases'])

    async def _on_before_startup():
        await on_before_startup(service_config)

    service_config = Configuration(
        storage=LocalStorageClient(
            root_path=databases_path / 'storage',
            bucket_name=Constants.namespace
        )
    )
    server_options = ServerOptions(
        root_path="",
        http_port=env['portsBook']['cdn-sessions-storage'],
        base_path="",
        middlewares=[FastApiMiddleware(AuthLocalMiddleware, {})],
        on_before_startup=_on_before_startup,
        ctx_logger=ConsoleContextLogger()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
