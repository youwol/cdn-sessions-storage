import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Union, Any, Coroutine, Dict, Type, Callable

from youwol_utils import (
    find_platform_path, get_headers_auth_admin_from_env,
    get_headers_auth_admin_from_secrets_file, log_info, StorageClient, LocalStorageClient, AuthClient, CacheClient,
    get_youwol_environment
)
from youwol_utils.context import ContextLogger, DeployedContextLogger
from youwol_utils.middlewares import Middleware
from youwol_utils.middlewares.authentication_local import AuthLocalMiddleware

AuthMiddleware = Union[Type[Middleware], Type[AuthLocalMiddleware]]


@dataclass(frozen=True)
class Configuration:
    open_api_prefix: str
    http_port: int
    base_path: str

    auth_middleware: AuthMiddleware
    auth_middleware_args: Dict[str, any]
    storage: Union[StorageClient, LocalStorageClient]
    admin_headers: Union[Coroutine[Any, Any, Dict[str, str]], None]

    namespace: str = "cdn-sessions-storage"
    default_owner: str = "/youwol-users"
    cache_prefix: str = "cdn-sessions-storage_"
    unprotected_paths: Callable[[str], bool] = lambda url: \
        url.path.split("/")[-1] == "healthz" or url.path.split("/")[-1] == "openapi-docs"

    ctx_logger: ContextLogger = DeployedContextLogger()


async def get_tricot_config() -> Configuration:
    required_env_vars = ["AUTH_HOST", "AUTH_CLIENT_ID", "AUTH_CLIENT_SECRET", "AUTH_CLIENT_SCOPE"]
    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")
    openid_host = os.getenv("AUTH_HOST")

    log_info("Use tricot configuration", openid_host=openid_host)

    storage = StorageClient(
        bucket_name=Configuration.namespace,
        url_base="http://storage/api"
    )

    auth_client = AuthClient(url_base=f"https://{openid_host}/auth")
    cache_client = CacheClient(host="redis-master.infra.svc.cluster.local", prefix=Configuration.cache_prefix)

    return Configuration(
        open_api_prefix='/applications',
        http_port=8080,
        base_path="",
        storage=storage,
        admin_headers=get_headers_auth_admin_from_env(),
        auth_middleware=Middleware,
        auth_middleware_args={
            "auth_client": auth_client,
            "cache_client": cache_client,
            "unprotected_paths": Configuration.unprotected_paths
        },
    )


async def get_remote_clients_config(url_cluster) -> Configuration:
    openid_host = "gc.auth.youwol.com"
    storage = StorageClient(
        url_base=f"https://{url_cluster}/api/storage",
        bucket_name=Configuration.namespace
    )
    auth_client = AuthClient(url_base=f"https://{openid_host}/auth")
    cache_client = CacheClient(host="redis-master.infra.svc.cluster.local", prefix=Configuration.cache_prefix)
    return Configuration(
        open_api_prefix='/applications',
        http_port=1000,
        base_path="",
        storage=storage,
        admin_headers=get_headers_auth_admin_from_secrets_file(
            file_path=find_platform_path() / "secrets" / "tricot.json",
            url_cluster=url_cluster,
            openid_host=openid_host
        ),
        auth_middleware=Middleware,
        auth_middleware_args={
            "auth_client": auth_client,
            "cache_client": cache_client,
            "unprotected_paths": Configuration.unprotected_paths
        },
    )


async def get_remote_clients_gc_config() -> Configuration:
    return await get_remote_clients_config("gc.platform.youwol.com")


async def get_full_local_config() -> Configuration:
    conf = await get_youwol_environment()
    storage = LocalStorageClient(
        root_path=Path(conf['pathsBook']['databases']) / 'storage',
        bucket_name=Configuration.namespace
    )
    return Configuration(
        open_api_prefix='',
        http_port=2100,
        base_path="",
        storage=storage,
        admin_headers=None,
        auth_middleware=AuthLocalMiddleware,
        auth_middleware_args={}
    )


configurations = {
    'tricot': get_tricot_config,
    'remote-clients': get_remote_clients_gc_config,
    'full-local': get_full_local_config,
}

current_configuration = None


async def get_configuration():
    global current_configuration
    if current_configuration:
        return current_configuration

    current_configuration = await configurations[sys.argv[1]]()
    return current_configuration
