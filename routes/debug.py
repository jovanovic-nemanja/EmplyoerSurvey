import aiohttp_csrf
import aiohttp_jinja2

from auth import init_auth
from common import ENV
from sess import init_session


@aiohttp_jinja2.template('login-test.html')  # TODO: Remove this function
async def login_test(request):
    #session = await init_session(request)
    auth = await init_auth(request, protect=False)
    csrf_token = await aiohttp_csrf.generate_token(request)
    # return aiohttp_jinja2.render_template('index.html', request, context)
    return {'page_title': "Home", 'csrf': csrf_token, 'auth': auth, 'msg': '', 'ENV': ENV}
