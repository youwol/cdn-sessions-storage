import os

from config_common import on_before_startup
from youwol_cdn_sessions_storage import Configuration, Constants
from youwol_utils import StorageClient, RedisCacheClient, get_authorization_header
from youwol_utils.clients.oidc.oidc_config import OidcInfos
from youwol_utils.clients.oidc.oidc_config import PrivateClient
from youwol_utils.context import DeployedContextReporter
from youwol_utils.middlewares import AuthMiddleware, JwtProviderCookie
from youwol_utils.servers.fast_api import FastApiMiddleware, ServerOptions, AppConfiguration


async def get_configuration():
    required_env_vars = [
        "OPENID_BASE_URL",
        "OPENID_CLIENT_ID",
        "OPENID_CLIENT_SECRET",
        "REDIS_HOST"
    ]

    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")

    openid_base_url = os.getenv("OPENID_BASE_URL")
    openid_client_id = os.getenv("OPENID_CLIENT_ID")
    openid_client_secret = os.getenv("OPENID_CLIENT_SECRET")
    oidc_client = PrivateClient(client_id=openid_client_id, client_secret=openid_client_secret)
    openid_infos = OidcInfos(base_uri=openid_base_url, client=oidc_client)

    redis_host = os.getenv("REDIS_HOST")
    jwt_cache = RedisCacheClient(host=redis_host, prefix='jwt_cache')

    async def _on_before_startup():
        await on_before_startup(service_config)

    service_config = Configuration(
        storage=StorageClient(
            url_base="http://storage/api",
            bucket_name=Constants.namespace
        ),
        admin_headers=await get_authorization_header(openid_infos)
    )
    server_options = ServerOptions(
        root_path='/api/cdn-sessions-storage',
        http_port=8080,
        base_path="",
        middlewares=[
            FastApiMiddleware(
                AuthMiddleware, {
                    'openid_infos': openid_infos,
                    'predicate_public_path': lambda url:
                    url.path.endswith("/healthz"),
                    'jwt_providers': [JwtProviderCookie(
                        jwt_cache=jwt_cache,
                        openid_infos=openid_infos
                    )],
                }
            )
        ],
        on_before_startup=_on_before_startup,
        ctx_logger=DeployedContextReporter()
    )
    return AppConfiguration(
        server=server_options,
        service=service_config
    )
