import aiohttp_csrf
import aiohttp_jinja2

from auth import init_auth
from common import ENV
from sess import init_session


# section index
@aiohttp_jinja2.template('index.html')
@aiohttp_csrf.csrf_exempt
async def index(request):
    #session = await init_session(request)
    auth = await init_auth(request, protect=False)
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {
        'page_title': "Employee Survey Intelligence",
        'csrf': csrf_token,
        'auth': auth,
        'msg': '',
        'ENV': ENV,
        'menu_padding_off': True
    }


# section index
@aiohttp_jinja2.template('learn.html')
@aiohttp_csrf.csrf_exempt
async def learn(request):
    #session = await init_session(request)
    auth = await init_auth(request, protect=False)
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {
        'page_title': "Learn Hiyer (It's easy)",
        'csrf': csrf_token,
        'auth': auth, 'msg': '',
        'ENV': ENV,
        'menu_padding_off': True,
    }

