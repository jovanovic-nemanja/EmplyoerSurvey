import aiohttp_csrf
import aiohttp_jinja2
from aiomysql import DictCursor

from auth import init_auth
from common import ENV
from sess import init_session


@aiohttp_jinja2.template('admin_home.html')
async def admin_home(request):
    #session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='admin')
    # test = session.data
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("SELECT * FROM users")
            _users = await cur.fetchall()
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {'page_title': "Administration", 'csrf': csrf_token, 'auth': auth,  'users': _users,
            'ENV': ENV}


@aiohttp_jinja2.template('admin_users.html')
async def admin_users(request):
    #session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='admin')
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("SELECT * FROM users")
            _users = await cur.fetchall()
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {'page_title': "Admin Users", 'csrf': csrf_token, 'auth': auth,  'users': _users,
            'ENV': ENV}


@aiohttp_jinja2.template('admin_surveys.html')
async def admin_surveys(request):
    #session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='admin')
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("SELECT * FROM users")
            _users = await cur.fetchall()
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {'page_title': "Admin Users", 'csrf': csrf_token, 'auth': auth,  'users': _users,
            'ENV': ENV}


@aiohttp_jinja2.template('admin_algo.html')
async def admin_algo(request):
    #session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='admin')
    """async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("SELECT * FROM users")
            _users = await cur.fetchall()"""
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {'page_title': "Admin Algo", 'csrf': csrf_token, 'auth': auth,
            'ENV': ENV}
