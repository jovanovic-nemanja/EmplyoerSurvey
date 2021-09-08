import os
import re
from os.path import abspath, dirname
from common import log

BASE_PATH = dirname(abspath(__file__))


def to_bool(astr):
    return bool(astr.strip().lower() in ('true', '1')) if isinstance(astr, str) else bool(int(astr))


async def register_globals(app):
    app['referer_regex'] = re.compile("^[a-zA-Z0-9/_]+$")
    return app


env_params = {
    'SITE_USE_MULTITHREAD': to_bool,
    'SITE_HOST': str,
    'PORT': int,
    'SITE_NAME': str,
    'SITE_DEBUG_TOOLBAR': to_bool,
    'SITE_UVLOOP': to_bool,
    'SITE_UPLOAD_DIR': str,
    'SITE_GEO_PATH': str,
    'SITE_COOKIE_NAME': str,
    'SITE_LOG_LEVEL': str,
    'SITE_SSL': to_bool,
    'EMAIL_SENDGRID_KEY': str,
    'EMAIL_DEFAULT_SENDER': str,
    'SMS_TWILIO_ACCOUNT_SID': str,
    'SMS_TWILIO_AUTH_TOKEN': str,
    'SMS_TWILIO_NUMBER': str,
    'MYSQL_HOSTNAME': str,
    'MYSQL_PORT': int,
    'MYSQL_DATABASE': str,
    'MYSQL_USERNAME': str,
    'MYSQL_PASSWORD': str,
    'REDIS_URL': str,
    'REDIS_HOST': str,
    'REDIS_PORT': int,
    'BAUTH_ENABLED': to_bool,
    'BAUTH_USERNAME': str,
    'BAUTH_PASSWORD': str,
    'CSRF_FORM_FIELD': str,
    'CSRF_SESSION_NAME': str,
    'CSRF_SECRET': str,
    'JWT_SECRET': str,
    'ARANGO_HOST': str,
    'ARANGO_PORT': int,
    'ARANGO_USER': str,
    'ARANGO_PASSWORD': str,
    'ARANGO_DB': str,
    'ARANGO_GRAPH_ROOT': str,
    'ARANGO_GRAPH_NAME': str,
    'SITE_DOMAIN': str,
    'IN_PRODUCTION': to_bool,
    'ALLOW_DUPE_NOTIFY': to_bool,
    'DUPE_BLOCK_MINS': int
}

environment_vars = os.environ
ENV = {}
for env_key, type_setter in env_params.items():
    try:
        if from_env := environment_vars.get(env_key):
            try:
                ENV[env_key] = type_setter(from_env)
            except ValueError as ex:
                log.warning("Env var 'value' error, unable to set:", env_key)
                continue
    except KeyError:
        log.warning("Env var 'key' error, unable to set:", env_key)
        continue
