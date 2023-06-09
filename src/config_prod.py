import os

from youwol.backends.cdn_sessions_storage import Configuration, Constants
from youwol.utils import StorageClient, RedisCacheClient
from youwol.utils.clients.oidc.oidc_config import OidcInfos
from youwol.utils.clients.oidc.oidc_config import PrivateClient
from youwol.utils.context import DeployedContextReporter
from youwol.utils.middlewares import AuthMiddleware, JwtProviderCookie
from youwol.utils.servers.env import REDIS, OPENID_CLIENT, Env
from youwol.utils.servers.fast_api import (
    FastApiMiddleware,
    ServerOptions,
    AppConfiguration,
)


async def get_configuration():
    required_env_vars = OPENID_CLIENT + REDIS

    not_founds = [v for v in required_env_vars if not os.getenv(v)]
    if not_founds:
        raise RuntimeError(f"Missing environments variable: {not_founds}")

    openid_base_url = os.getenv(Env.OPENID_BASE_URL)
    openid_client_id = os.getenv(Env.OPENID_CLIENT_ID)
    openid_client_secret = os.getenv(Env.OPENID_CLIENT_SECRET)
    oidc_client = PrivateClient(
        client_id=openid_client_id, client_secret=openid_client_secret
    )
    openid_infos = OidcInfos(base_uri=openid_base_url, client=oidc_client)

    redis_host = os.getenv(Env.REDIS_HOST)
    auth_cache = RedisCacheClient(host=redis_host, prefix="auth_cache")

    service_config = Configuration(
        storage=StorageClient(
            url_base="http://storage/api", bucket_name=Constants.namespace
        ),
    )
    server_options = ServerOptions(
        root_path="/api/cdn-sessions-storage",
        http_port=8080,
        base_path="",
        middlewares=[
            FastApiMiddleware(
                AuthMiddleware,
                {
                    "openid_base_uri": openid_base_url,
                    "predicate_public_path": lambda url: url.path.endswith("/healthz"),
                    "jwt_providers": [
                        JwtProviderCookie(
                            auth_cache=auth_cache, openid_infos=openid_infos
                        )
                    ],
                },
            )
        ],
        ctx_logger=DeployedContextReporter(),
    )
    return AppConfiguration(server=server_options, service=service_config)
