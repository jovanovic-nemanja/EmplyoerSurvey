import io
import json
import csv
import re

import aiohttp_csrf
import pyqrcodeng as pyqrcode
from aiohttp import web
from aiomysql import DictCursor, IntegrityError
from passlib import pwd
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from passlib.context import CryptContext

from auth import init_auth
from common import ENV, log, send_email, send_sms, strip_nonnumeric, linkify
from graph import load_collections, load_edge_collection, load_graph
from sess import init_session
from validate import (ADD_USER_VALIDATOR_EMAIL,
                      ADD_USER_VALIDATOR_PHONE, ValidationError, validate_json)


def date_to_str(dt):
    return dt.isoformat()


@aiohttp_csrf.csrf_exempt
async def list_users(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='admin')
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                "SELECT login, is_superuser, banned, user_level, email_address, \
                    first_name, last_name, mobile_number, is_new_user, gravatar, \
                        address, company_name FROM `users`")
            users = await cur.fetchall()

    return web.json_response(users, dumps=json.dumps)


@aiohttp_csrf.csrf_exempt
async def list_surveys(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='admin')
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("SELECT id FROM surveys")
            users = await cur.fetchall()

    return web.json_response(users, dumps=json.dumps)


async def add_mailing_list_recipient(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    form = await request.post()
    email_address = form.get('email_address')
    mailing_list = form.get('mailing_list')
    if email_address is None:
        raise web.HTTPBadRequest()
    if mailing_list is None:
        mailing_list = 1
    error_msg = ""
    success = False
    try:
        async with request.app['mysql'].acquire() as conn:
            async with conn.cursor(DictCursor) as cur:
                await cur.execute(
                    """
                    INSERT INTO mailing_recipients
                    SET
                        email_address = %s,
                        mailing_list = %s
                    """, (email_address, mailing_list,))
                success = True
    except IntegrityError:
        error_msg = "You're already on the list. Check your inbox for confirmation."
    return web.json_response({"success": success, "error": error_msg}, dumps=dumps)


async def submit_contact_form(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    form = await request.post()
    recipient_name = form.get('name')
    recipient_email = form.get('email')
    subject = form.get('subject')
    message = form.get('message')
    if None in (recipient_name, recipient_email, subject, message):
        raise web.HTTPBadRequest()
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                """
                SELECT * FROM users
                WHERE
                    is_superuser = 1
                """)
            admins = await cur.fetchall()
            for admin in admins:
                send_email(
                    admin['email_address'],
                    subject,
                    message
                )
                send_sms(admin['mobile_number'],
                         f"""A visitor of CubeAtomizers.com has submitted a message
                         via the contact form. It's in your mailbox.""")
    return web.json_response({"success": True}, dumps=json.dumps)


@aiohttp_csrf.csrf_exempt
async def do_add_employee(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    arango = request.app['arango']
    graph_name = 'surveys'
    fresh = False
    graph = None
    try:
        graph = load_graph(arango, graph_name)
    except Exception as ex:
        log.exception(ex)
    vtx_collections = load_collections(graph, [
        ('Company',),
        ('Employee',),
        ('Question',),
        (ENV.ARANGO_GRAPH_ROOT,)
    ], _fresh=fresh)
    company_of_site = load_edge_collection(
        'Company', ENV.ARANGO_GRAPH_ROOT, graph)
    vtx_collections[ENV.SITE_NAME].insert({
        '_key': '1',
        'node_name': f"{ENV.ARANGO_GRAPH_ROOT}Root"
    })
    employee_of_company = load_edge_collection('Employee', 'Company', graph)
    question_of_employee = load_edge_collection('Question', 'Employee', graph)

    log.info(f'Graph {graph_name} loaded.')

    return web.json_response({"success": True}, dumps=json.dumps)


@aiohttp_csrf.csrf_exempt
async def do_update_employee(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    form = await request.post()
    employee_id = form.get('employee_id')
    department = form.get('department')

    if (auth['is_employer']):
        async with request.app['mysql'].acquire() as conn:
            async with conn.cursor(DictCursor) as cur:
                await cur.execute("""
                    UPDATE users SET dept = %s WHERE id = %s
                """, (department, employee_id))
                await conn.commit()

        return web.json_response({'success': True, 'employee_id': employee_id},
                                 dumps=json.dumps)

    return web.json_response({'success': False}, dumps=json.dumps)


@aiohttp_csrf.csrf_exempt
async def do_delete_employee(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    form = await request.post()
    employee_id = form.get('employee_id')

    if (auth['is_employer']):
        async with request.app['mysql'].acquire() as conn:
            async with conn.cursor(DictCursor) as cur:
                await cur.execute("""
                    DELETE FROM users WHERE id = %s
                """, (employee_id))
                await conn.commit()

        return web.json_response({'success': True, 'employee_id': employee_id},
                                 dumps=json.dumps)

    return web.json_response({'success': False}, dumps=json.dumps)


@aiohttp_csrf.csrf_exempt
async def do_add_company(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    # arango = request.app['arango']

    return web.json_response({"success": True}, dumps=json.dumps)


async def do_invite_user(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    udat = await request.post()
    # udat = await request.get_json()

    try:
        if 'email_address' in udat and udat['email_address'] != '':
            validator = ADD_USER_VALIDATOR_EMAIL
        else:
            validator = ADD_USER_VALIDATOR_PHONE
        uin = validate_json(udat, validator)
        if 'email_address' not in uin or uin['email_address'] == '':
            email_address = None
        else:
            email_address = uin['email_address']
        if 'mobile_number' not in uin or uin['mobile_number'] == '':
            mobile_number = None
        else:
            mobile_number = uin['mobile_number']
        if email_address is None and mobile_number is None:
            return web.json_response({
                "msg": "Either email or phone number required."})
    except KeyError as ex:
        return web.json_response({"msg": "Missing input field in request."})
    except ValidationError as ex:
        return web.json_response({"msg": str(ex)})

    async with request.app['mysql'].acquire() as db:
        async with db.cursor(DictCursor) as cur:
            await cur.execute(f"""
                                    SELECT *
                                    FROM
                                        users
                                    WHERE
                                        email_address = %s
                                        OR
                                        mobile_number = %s
                                    LIMIT 1
                                    """,
                              (email_address, mobile_number,))
            user_existing = await cur.fetchone()
            if user_existing:
                return web.json_response({
                    "msg": "User already exists. Cannot add."
                })
            else:
                temp_pass = pwd.genword(length=15, charset="ascii_72")
                invite_code = pwd.genphrase()
                hashed_pass = request.app['argon2'].hash(temp_pass)
                mobile_number_no = ''.join(
                    ch for ch in mobile_number if ch.isdigit())
                mobile_number_no = int(mobile_number_no)
                await cur.execute(f"""
                    INSERT INTO users
                    (email_address, mobile_number, `password_hash`, user_level,
                        invite_code, first_name, last_name, mobile_number_no)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (email_address, mobile_number, hashed_pass, uin['user_level'],
                      invite_code, uin['first_name'], uin['last_name'],
                      mobile_number_no,))
                await db.commit()

                if mobile_number is not None:
                    client = Client(ENV.SMS_TWILIO_ACCOUNT_SID,
                                    ENV.SMS_TWILIO_AUTH_TOKEN)
                    message = client.messages \
                        .create(
                            body=f"""Hi {uin['first_name']}. You've been invited \
                                to {ENV.SITE_NAME}! Join your co-workers
                        here: https://{ENV.SITE_DOMAIN} {invite_code}""",
                            from_=ENV.SMS_TWILIO_NUMBER,
                            to=mobile_number
                        )
                if email_address is not None:
                    qr_buffer = io.BytesIO()
                    qr = pyqrcode.create(invite_code)
                    qr.svg(qr_buffer, scale=6)
                    qr_buffer.seek(0)
                    invite_qr = qr_buffer.read().decode('utf-8')
                    message = Mail(
                        from_email='app@CubeAtomizers.com',
                        to_emails=uin['email_address'],
                        subject=f"{uin['first_name']} - Your Cube Atomizers inventory \
                            app invitation...",
                        html_content=f"""
                            Hi {uin['first_name']},
                            <p>You've been invited to the Cube Atomizers Inventory app!</p>
                            <p>Get it here for Android:
                                <a href="https://www.cubeatomizers.com/download/inventory/Cube-Atomizers-Inventory.apk">
                                    Cube-Atomizers-Inventory.apk
                                </a>
                            </p>
                            <p>Your invite code is: <strong>{invite_code}</strong></p>
                            <p>
                                <center>{invite_qr}</center>
                            </p>
                        """)
                    try:
                        sg = SendGridAPIClient(ENV.EMAIL_SENDGRID_KEY)
                        response = sg.send(message)
                        '''
                        print(response.status_code)
                        print(response.body)
                        print(response.headers)'''
                    except Exception as e:
                        log.exception(e)  # return jsonify(msg=e)
                        return web.json_response({
                            'success': False,
                            'error': 'Error sending invite email(s).'
                        })
                return web.json_response({
                    'msg': f"{uin['first_name']} has been invited.",
                    'mob': mobile_number
                })


@aiohttp_csrf.csrf_exempt
async def do_invite_employees(request):
    auth = await init_auth(request, protect=True, permission='user')
    form = await request.post()
    department_id = form.get('department')
    input_type = form.get('input_type')

    if auth['is_employer']:
        async with request.app['mysql'].acquire() as conn:
            async with conn.cursor(DictCursor) as cur:
                await cur.execute("""
                    SELECT * FROM departments WHERE id = %s
                """, (department_id,))
                department = await cur.fetchone()

                if department is None:
                    return web.json_response({
                        'success': False,
                        'msg': 'Incorrect department'
                    })

                sql_query = """
                    INSERT INTO users
                    SET
                        user_level = 1,
                        referring_user = %s,
                        is_employer = %s,
                        org = %s,
                        dept = %s,
                        company_name = %s,
                        password_hash = %s,
                        invite_code = %s
                    """
                sql_values = (auth['user_id'],
                              0,
                              auth['org'],
                              department_id,
                              auth['company_name'],)

                crypt_context = CryptContext(schemes=["argon2"])
                invite_cnt = 0

                if input_type == 'text':
                    invite_emails = form.get('invite_emails')
                    mobile_numbers = form.get('mobile_numbers')
                    if invite_emails:
                        invite_emails = invite_emails.split(",")
                        for email in invite_emails:
                            if not validate_email(email):
                                continue

                            await cur.execute("""
                                SELECT *
                                FROM users
                                WHERE email_address = %s
                            """, (email,))
                            inv_exists = await cur.fetchone()

                            if inv_exists and not inv_exists['is_new_user']:
                                continue

                            if inv_exists:
                                this_uid = inv_exists['id']
                                invite_code = inv_exists['invite_code']

                            else:
                                invite_code = await unique_invite(request.app)
                                temp_pass = pwd.genword(
                                    length=15, charset="ascii_72")
                                hashed_pass = crypt_context.hash(temp_pass)
                                await cur.execute(f'{sql_query}, email_address = %s',
                                                  sql_values +
                                                  (hashed_pass,
                                                   invite_code.replace(
                                                       ' ', ''),
                                                   email,))
                                await conn.commit()

                                this_uid = cur.lastrowid

                                login = f"user{this_uid}"
                                await cur.execute("UPDATE users SET login = %s \
                                    WHERE id = %s", (login,
                                                     this_uid,))
                                await conn.commit()

                            msg = f"Your employer has invited you to Hiyer. Sign up {ENV.URL_PROTO}{ENV.SITE_DOMAIN}/i/{invite_code}"

                            await cur.execute("""
                                INSERT INTO notifications
                                SET
                                user_id = %s,
                                calling_path = %s,
                                title = 'Hiyer Invite',
                                msg = %s,
                                icon = 'flat-color-icons:invite',
                                seen = 1
                            """, (this_uid,
                                  f"/i/{invite_code}",
                                  msg))
                            await conn.commit()

                            send_email(
                                email,
                                'Hiyer Invite',
                                linkify(msg)
                            )

                            invite_cnt += 1

                    if mobile_numbers:
                        mobile_numbers = mobile_numbers.split(",")
                        for num in mobile_numbers:
                            # TODO: validate phone number
                            await cur.execute("""
                                SELECT *
                                FROM users
                                WHERE mobile_number = %s
                            """, (num,))
                            inv_exists = await cur.fetchone()

                            if inv_exists and not inv_exists['is_new_user']:
                                continue

                            if inv_exists:
                                this_uid = inv_exists['id']
                                invite_code = inv_exists['invite_code']

                            else:
                                invite_code = await unique_invite(request.app)
                                temp_pass = pwd.genword(
                                    length=15, charset="ascii_72")
                                hashed_pass = crypt_context.hash(temp_pass)
                                await cur.execute(f'{sql_query}, mobile_number = %s',
                                                  sql_values +
                                                  (hashed_pass,
                                                   invite_code.replace(
                                                       ' ', ''),
                                                   f"+{strip_nonnumeric(num)}",))
                                await conn.commit()

                                this_uid = cur.lastrowid

                                login = f"user{this_uid}"
                                await cur.execute("UPDATE users SET login = %s \
                                    WHERE id = %s", (login,
                                                     this_uid,))
                                await conn.commit()

                            msg = f"Your employer has invited you to Hiyer. Sign up {ENV.URL_PROTO}{ENV.SITE_DOMAIN}/i/{invite_code}"

                            await cur.execute("""
                                INSERT INTO notifications
                                SET
                                    user_id = %s,
                                    calling_path = 'invite_user',
                                    title = 'Hiyer Invite',
                                    msg = %s,
                                    icon = 'flat-color-icons:invite'
                            """, (this_uid, msg,))
                            await conn.commit()

                            send_sms(
                                num,
                                linkify(msg)
                            )

                            invite_cnt += 1

                else:
                    csv_file = form.get('invite_csv').file
                    invite_type = form.get('invite_type')

                    if csv_file:
                        data_set = csv_file.read().decode('UTF-8')
                        # setup a stream which is when we loop through each line we are able to handle a data in a stream
                        io_string = io.StringIO(data_set)
                        for row in csv.reader(io_string, delimiter=',', quotechar="|"):
                            for txt in row:
                                if invite_type == 'email' and validate_email(txt):
                                    email = txt
                                    await cur.execute("""
                                        SELECT *
                                        FROM users
                                        WHERE email_address = %s
                                    """, (email,))
                                    inv_exists = await cur.fetchone()

                                    if inv_exists and not inv_exists['is_new_user']:
                                        continue

                                    if inv_exists:
                                        this_uid = inv_exists['id']
                                        invite_code = inv_exists['invite_code']

                                    else:
                                        invite_code = await unique_invite(request.app)
                                        temp_pass = pwd.genword(
                                            length=15, charset="ascii_72")
                                        hashed_pass = crypt_context.hash(
                                            temp_pass)
                                        await cur.execute(f'{sql_query}, email_address = %s',
                                                          sql_values +
                                                          (hashed_pass,
                                                           invite_code.replace(
                                                               ' ', ''),
                                                           email,))
                                        await conn.commit()

                                        this_uid = cur.lastrowid

                                        login = f"user{this_uid}"
                                        await cur.execute("UPDATE users SET login = %s \
                                            WHERE id = %s", (login,
                                                             this_uid,))

                                    msg = f"Your employer has invited you to Hiyer. Sign up {ENV.URL_PROTO}{ENV.SITE_DOMAIN}/i/{invite_code}"

                                    await cur.execute("""
                                        INSERT INTO notifications
                                        SET
                                        user_id = %s,
                                        calling_path = %s,
                                        title = 'Hiyer Invite',
                                        msg = %s,
                                        icon = 'flat-color-icons:invite',
                                        seen = 1
                                    """, (this_uid,
                                          f"/i/{invite_code}",
                                          msg))
                                    await conn.commit()

                                    send_email(
                                        email,
                                        'Hiyer Invite',
                                        linkify(msg)
                                    )

                                    invite_cnt += 1

                return web.json_response({
                    'success': not not invite_cnt,
                    'msg': f'Invited {invite_cnt} employees.' if invite_cnt else 'No valid emails or phone numbers given.'
                })


# Function to gen codes
async def unique_invite(app):
    exist = True
    async with app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            while exist is not None:
                invite_code = pwd.genword(length=6, charset="ascii_62")
                await cur.execute(
                    """
                    SELECT `id`
                    FROM users
                    WHERE invite_code = %s
                    LIMIT 1
                """, (invite_code,))
                exist = await cur.fetchone()

    return invite_code


def validate_email(email):
    regex = '^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))'

    if(re.search(regex, email)):
        return True

    return False
