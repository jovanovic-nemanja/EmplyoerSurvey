import asyncio

import aiohttp_csrf
import aiohttp_jinja2
import jwt
from aiohttp import web
from aiohttp_basicauth import BasicAuthMiddleware
from aiohttp_jwt import JWTMiddleware, login_required
from auth import init_auth
from common import ENV, log
from http_errors import http_responses
from sess import init_session


async def get_jwt_token(request):
    return jwt.encode(
        {"username": "johndoe", "scopes": ["username:johndoe"]}, ENV.JWT_SECRET
    )


def create_error_middleware(overrides):
    @web.middleware
    @aiohttp_csrf.csrf_exempt
    async def error_middleware(request, handler):
        ##session = await init_session(request)
        auth = await init_auth(request, protect=False)
        try:
            return await handler(request)
        except web.HTTPException as ex:
            if ex.status == 302:
                raise
            else:
                log.error(f"Exception in {request.rel_url}")
                log.exception(ex)
                return aiohttp_jinja2.render_template(
                    "http_error.html", request,
                    {
                        "http_error_txt": str(ex),  # TODO: A dict of nicer http status texts
                        "http_code": ex.status,
                        "http_error_ext": http_responses[ex.status][1],
                        "ENV": ENV,
                        'auth': auth
                    }, status=ex.status
                )
        except asyncio.CancelledError:
            raise
        except Exception as ex:
            log.exception(ex)
            return aiohttp_jinja2.render_template(
                "http_error.html", request,
                {
                    "http_error_txt": str(ex),
                    'http_code': 400,
                    'http_error_ext': None,
                    'ENV': ENV,
                    #
                    'auth': auth
                }, status=400
            )
    
    return error_middleware


async def mod_server_header(request, response):
    response.headers['Server'] = 'Not Apache'


async def get_token(request):
    return jwt.encode({"username": "johndoe", "scopes": ["user:admin"]}, secret)


def setup_middlewares(app):
    # BasicAuth
    if ENV.BAUTH_ENABLED:
        auth = BasicAuthMiddleware(username=ENV.BAUTH_USERNAME,
                                   password=ENV.BAUTH_PASSWORD,
                                   force=True)
        app.middlewares.append(auth)
    # Custom header
    app.on_response_prepare.append(mod_server_header)
    # HTTP Codes
    error_middleware = create_error_middleware({})
    app.middlewares.append(error_middleware)
    # CSRF
    csrf_policy = aiohttp_csrf.policy.FormPolicy(ENV.CSRF_FORM_FIELD)
    csrf_storage = aiohttp_csrf.storage.SessionStorage(session_name=ENV.CSRF_FORM_FIELD,
                                                       secret_phrase=ENV.CSRF_SECRET)  # previous was 15 bits
    aiohttp_csrf.setup(app, policy=csrf_policy, storage=csrf_storage)  # , error_renderer=CustomException
    # JWT
    # app.middlewares.append(
    #     JWTMiddleware(
    #         ENV.JWT_SECRET,
    #         request_property="jwt",
    #         token_getter=get_token,
    #         credentials_required=False
    #     )
    # )
    app.middlewares.append(aiohttp_csrf.csrf_middleware)
# app.middlewares.append(jwt_middleware)
