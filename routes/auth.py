import uuid

import aiohttp_csrf
import aiohttp_jinja2
import aiohttp_session
import jwt
import validators
from aiohttp import web
from aiohttp.web_response import Response
from aiohttp_security import (forget, remember)
from aiomysql import DictCursor
from cerberus import Validator

from auth import init_auth
from auth.policy import check_credentials, register_account
from common import ENV, log, send_email, send_sms
from sess import Alert, Session, init_session


# section do_login
async def do_login(request):
    session = Session(await aiohttp_session.get_session(request))
    auth = await init_auth(request)
    alerter = Alert(web, session)
    response = Response()
    csrf_token = await aiohttp_csrf.generate_token(request)
    form = await request.post()
    username = form.get('username')
    password = form.get('password')
    login_check, banned, is_employer = await check_credentials(request.app['mysql'], username, password)
    # FIXME: better for api...
    """if not login_check or banned:
        raise web.HTTPUnauthorized"""

    if login_check and not banned:
        await remember(request, response, username)
        if (is_employer):
            await alerter.info("You're logged in", '/dash')
        else:
            await alerter.info("You're logged in", '/s')
    # raise web.HTTPFound('/user/dash')
    else:
        # context = {'page_title': "Home", 'auth': auth, 'csrf': csrf_token}
        # response = aiohttp_jinja2.render_template('index.html', request, context)
        await alerter.error("Invalid login credentials", '/login')


# section do_register
@aiohttp_csrf.csrf_exempt
async def do_register(request):
    session = Session(await aiohttp_session.get_session(request))
    auth = await init_auth(request, protect=False)
    alerter = Alert(web, session)
    response = Response()
    form = request['ws_post'] if 'ws_post' in request else await request.post()
    username = form.get('username')
    password = form.get('password')
    email_address = form.get('email_address')
    password_confirm = form.get('password_repeat')
    first_name = form.get('first_name')
    last_name = form.get('last_name')
    mobile_number = form.get('mobile_number')
    invite_code = form.get('invite_code')
    account_type = form.get('account_type')
    company_name = form.get('org_name')

    registered, error_msg = await register_account(request.app['mysql'],
                                                   username,
                                                   password, password_confirm,
                                                   email_address, first_name,
                                                   last_name, mobile_number,
                                                   account_type, invite_code,
                                                   company_name)
    if registered:
        await alerter.success('Registration successful. You can now login.', '/login')
    else:
        error_path = '/register_employer' if account_type == 'employer' else '/register_employee'
        await alerter.error(error_msg, error_path)


async def validate_user_identifier(request, _identifier, _db_field='login'):
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            _query = f"""
				SELECT
					id, login, email_address,
					mobile_number
				FROM users
				WHERE {_db_field} = %s
				"""
            await cur.execute(_query, (_identifier,))
            return await cur.fetchone()


# section do_forgot_pwd
async def do_forgot_password(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    form = await request.post()
    user_email_phone = form.get('user_email_phone')

    # if validators.email(user_email_phone):

    def lookup_phone(phone_num):
        try:
            _res = request.app['twilio'].lookups.v1.phone_numbers(
                phone_num).fetch()
            return _res
        except Exception as ex:
            log.debug(ex)
            return False

    # phone_res = lookup_phone(user_email_phone)

    def validate_phone(_field, _mobile_number, error):
        try:
            if not lookup_phone(_mobile_number):
                error(_field, 'Value is not a valid phone number')
        except:
            return error(_field, 'Value is not a valid phone number')

    def validate_email(_field, _email_address, error):
        if not validators.email(_email_address):
            error(_field, 'Value is not a valid email address.')

    async def pwd_reset_code(_field, _value):
        pwd_uuid = str(uuid.uuid4())
        async with request.app['mysql'].acquire() as conn:
            async with conn.cursor(DictCursor) as cur:
                _query = f"""
					UPDATE users
					SET forgot_pwd_uuid = %s
					WHERE {_field} = %s
					"""
                await cur.execute(_query,
                                  (pwd_uuid, _value))
                return pwd_uuid

    v = Validator()
    user_field = None
    try:
        v.schema = {
            'email_address': {
                'type': 'string',
                'check_with': validate_email,
                'min': 5,
                'max': 255
            }
        }
        if v.validate({
            "email_address": user_email_phone
        }):
            user_field = 'email_address'
        v.schema = {
            'mobile_number': {
                'type': 'string',
                'check_with': validate_phone,
                'min': 5,
                'max': 15
            }
        }
        if v.validate({'mobile_number': user_email_phone}):
            user_field = 'mobile_number'
        v.schema = {
            'login': {
                'type': 'string',
                'min': 1,
                'max': 16,
                'regex': '^[a-zA-Z0-9]+$'
            }
        }
        if v.validate({'login': user_email_phone}):
            user_field = 'login'

    except Exception as ex:
        log.exception(ex)
    finally:
        if user_field is not None:
            if user := await validate_user_identifier(request, user_email_phone, user_field):
                # TODO: Return error here.
                reset_code = await pwd_reset_code(user_field, user_email_phone)
                send_sms(user['mobile_number'],
                         f"""The {ENV.SITE_NAME} password reset link you requested: https://{ENV.SITE_DOMAIN}/pwd/{reset_code}""")
                send_email(user['email_address'],
                           f"{ENV.SITE_NAME} - Password Reset Link",
                           f"""
				           Here's the password reset link you requested: <a href="">https://{ENV.SITE_DOMAIN}/pwd/{reset_code}"></a>
				           <p>&nbsp;</p>
				           If you didn't request a password reset, don't worry. Your account is safe.
				           """)
                raise web.HTTPFound("/forgot_password")
            else:
                log.debug(f'No record of {user_email_phone} exists in db.')
                raise web.HTTPFound('/')
    # TODO: Alert here.
    log.error('input not valid')
    # raise web.HTTPFound('/forgot_password#error')
    # raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    context = {'page_title': f"Home", 'csrf': csrf_token,
               'auth': auth, 'ENV': ENV, 'sess': session.data}
    return aiohttp_jinja2.render_template('forgot_password.html', request, context)


# section forgot_pwd
async def forgot_password(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    csrf_token = await aiohttp_csrf.generate_token(request)
    context = {'page_title': f"Bypass Login",
               'csrf': csrf_token, 'auth': auth, 'ENV': ENV}
    return aiohttp_jinja2.render_template('forgot_password.html', request, context)


# section register
@aiohttp_jinja2.template('register.html')
async def register(request):
    session = Session(await aiohttp_session.get_session(request))
    auth = await init_auth(request, protect=False)
    alerter = Alert(web, session)
    response = Response()
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {'page_title': "Register", 'auth': auth, 'msg': '', 'csrf': csrf_token, 'ENV': ENV}


# section register_employer
@aiohttp_jinja2.template('register_employer.html')
async def register_employer(request):
    # session = await init_session(request)
    session = Session(await aiohttp_session.get_session(request))
    auth = await init_auth(request, protect=False)
    alerter = Alert(web, session)
    response = Response()
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {'page_title': "Register Employer", 'auth': auth, 'msg': '', 'csrf': csrf_token, 'ENV': ENV}


# section register_employee
@aiohttp_jinja2.template('register_employee.html')
@aiohttp_csrf.csrf_exempt
async def register_employee(request):
    # session = await init_session(request)
    session = Session(await aiohttp_session.get_session(request))
    auth = await init_auth(request, protect=False)
    alerter = Alert(web, session)
    response = Response()
    csrf_token = await aiohttp_csrf.generate_token(request)
    invite_code = request.match_info['invite_code']
    log.debug(f"Displaying invite code page {invite_code}")
    mobile_number, email_address = '', ''
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                """
                SELECT * FROM users
                WHERE invite_code = %s
                """, (invite_code,))
            invited_user = await cur.fetchone()
            if invited_user is not None:
                mobile_number = invited_user['mobile_number']
                email_address = invited_user['email_address']
            log.debug(
                f"Loaded invite phone {invited_user['mobile_number']} | email: {invited_user['email_address']}")
    return {
        'page_title': "Register Employee",
        'auth': auth,
        'msg': '',
        'csrf': csrf_token,
        'ENV': ENV,
        'invite_code': invite_code if invite_code is not None else '',
        'email_address': email_address if email_address is not None else '',
        'mobile_number': mobile_number if mobile_number is not None else ''
    }


# section do_logout
@aiohttp_jinja2.template('index.html')
@aiohttp_csrf.csrf_exempt
async def do_logout(request):
    # session = await init_session(request)
    session = Session(await aiohttp_session.get_session(request))
    auth = await init_auth(request, protect=False)
    alerter = Alert(web, session)
    response = Response()
    auth['logged_in'] = False
    auth['username'] = None
    auth['user_id'] = None
    auth['message'] = 'logged out'
    csrf_token = await aiohttp_csrf.generate_token(request)
    # context = {'page_title': "Home", 'csrf': csrf_token, 'auth': auth, 'msg': '', 'ENV': ENV, 'sess': session.data}
    # response = aiohttp_jinja2.render_template('index.html', request, context)
    await forget(request, response)
    await alerter.info('Successfully logged out.', '/')
    return response


# section jwt_token
# @jwt_check_permissions(["app/user:admin", "username:johndoe"], comparison=match_any)
async def jwt_token(request):
    auth = await init_auth(request, protect=True, permission='user')
    return web.json_response(jwt.encode(
        {
            "username": auth.username,
            "scopes": [f"username:{auth.username}"]
        }, ENV.JWT_SECRET
    ))


# section login
@aiohttp_jinja2.template('login.html')
async def login(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    csrf_token = await aiohttp_csrf.generate_token(request)
    # return aiohttp_jinja2.render_template('index.html', request, context)
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("SELECT login FROM users")
            usernames = await cur.fetchall()
    return {'page_title': "Login", 'csrf': csrf_token, 'auth': auth, 'msg': '', 'ENV': ENV, 'usernames': usernames}
