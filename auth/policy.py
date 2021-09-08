from hashlib import md5
from secrets import compare_digest

import ujson
from aiohttp_security.abc import AbstractAuthorizationPolicy
from aiomysql import DictCursor
from cerberus import Validator
from passlib.hash import argon2
from passlib.pwd import genword

from common import format_cerberus, log


# TODO: Implement: from passlib.context import CryptContext | crypt_context = CryptContext(schemes=["argon2"])


class DBAuthorizationPolicy(AbstractAuthorizationPolicy):
    def __init__(self, dbengine):
        self.dbengine = dbengine
    
    async def authorized_userid(self, identity):
        async with self.dbengine.acquire() as conn:
            async with conn.cursor(DictCursor) as cur:
                await cur.execute("""SELECT *
                                    FROM
                                        users
                                    WHERE
                                        (login = %s
                                        OR
                                        email_address = %s)
                                        AND
                                        banned = 0
                                        """,
                                  (identity, identity,))
                _user = await cur.fetchone()
                return _user
    
    async def permits(self, identity, permission, context=None):
        if identity is None:
            return False
        async with self.dbengine.acquire() as conn:
            async with conn.cursor(DictCursor) as cur:
                await cur.execute("""SELECT
                                        COUNT(*) as cnt
                                    FROM
                                        users u
                                    JOIN
                                        permissions p
                                        ON
                                            p.user_id = u.id
                                            AND
                                            (p.perm_name = %s OR p.perm_name = 'admin')
                                    WHERE
                                        u.login = %s
                                    AND
                                        u.banned = 0
                                    LIMIT 1""",
                                  (permission, identity,))
                user = await cur.fetchone()
                return bool(user['cnt'])


async def check_credentials(mysql, username, password):
    async with mysql.acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("""SELECT
                                    id, password_hash, banned, aff_id, is_employer
                                FROM
                                    users
                                WHERE
                                    `login` = %s
                                    OR
                                    `email_address` = %s
                                """,
                              (username, username,))
            user = await cur.fetchone()
            if user is not None:
                verify = argon2.using(type='ID').verify(password, user['password_hash'])
                if verify and not user['banned']:
                    await cur.execute("""UPDATE
                                            users
                                        SET
                                            last_login_date = CURRENT_TIMESTAMP()
                                        WHERE
                                            id = %s""",
                                      (user['id'],))
                    await conn.commit()
                    await cur.close()
                return verify, user['banned'], user['is_employer']
            await cur.close()
    return False, None


async def register_account(mysql, username, password, password_confirm,
                           email_address, first_name, last_name, mobile_number,
                           account_type, invite_code=None, company_name=None):
    v = Validator()  # TODO: Add accepted_tos
    log.debug(f'Registerring with invite code: {invite_code}')
    invited_user = None
    async with mysql.acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            if invite_code is not None:
                await cur.execute(
                    """
                    SELECT *
                    FROM users
                    WHERE
                        invite_code = %s
                    """, (invite_code,))  # TODO: Maybe make this more secure
                invited_user = await cur.fetchone()
                if invited_user is None:
                    return False, f"Invalid invite code."
                account_type = 'employer' if invited_user['dept'] == 'management' else 'employee'
                mobile_number = mobile_number if mobile_number != invited_user['mobile_number'] else invited_user[
                    'mobile_number']
                email_address = email_address if email_address != invited_user['email_address'] else invited_user[
                    'email_address']
            v.schema = {
                "username": {
                    "type": "string",
                    "required": True,
                    "minlength": 3,
                    "maxlength": 16,
                    "regex": "^[a-zA-Z0-9]+$"
                },
                "invite_code": {
                    "type": "string",
                    "required": False,
                    "minlength": 1,
                    "maxlength": 7,
                    "regex": "^[a-zA-Z0-9]+$",
                    'nullable': True
                },
                "first_name": {
                    "type": "string",
                    "required": True,
                    "minlength": 1,
                    "maxlength": 25,
                    "regex": "^[a-zA-Z]+$"
                },
                "last_name": {
                    "type": "string",
                    "required": True,
                    "minlength": 1,
                    "maxlength": 25,
                    "regex": "^[a-zA-Z]+$"
                },
                "mobile_number": {
                    "type": "string",
                    "required": True,
                    "minlength": 3,
                    "maxlength": 50,
                    # "regex": r"^[\+\(]?\d+(?:[- \)\(]+\d+)+$"
                },
                "password": {
                    "type": 'string',
                    'required': True,
                    'minlength': 8,
                    'maxlength': 512,
                    'regex': '^[a-zA-Z0-9\s+()?$!@%^&*+()-=.,#;|]+$'
                },
                "email_address": {
                    "type": 'string',
                    'required': True,
                    'minlength': 1,
                    'maxlength': 255,
                    'regex': r'(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)'
                },
                "account_type": {
                    "type": 'string',
                    'required': True,
                    'minlength': 8,
                    'maxlength': 8,
                    'allowed': [
                        'employer',
                        'employee'
                    ]
                },
                "company_name": {
                    "type": 'string',
                    'required': False,
                    'minlength': 2,
                    'maxlength': 64,
                    'nullable': True
                }
            }
            if not compare_digest(password, password_confirm):
                return False, 'Passwords do not match.'
            if not v.validate({'username': username,
                               'invite_code': invite_code,
                               'password': password,
                               'first_name': first_name,
                               'last_name': last_name,
                               'mobile_number': mobile_number,
                               'email_address': email_address,
                               'account_type': account_type,
                               'company_name': company_name}):
                return False, format_cerberus(v.errors)
            email_md5 = md5(email_address.lower().encode('utf-8')).hexdigest()
            if invite_code is not None:
                await cur.execute("""SELECT
                                        *
                                    FROM
                                        users
                                    WHERE
                                        (login = %s
                                        OR
                                        email_address = %s)
                                        AND
                                        invite_code = %s""",
                                  (username, email_address, invite_code,))
                user = await cur.fetchone()
                invited_user = user
            else:
                await cur.execute(
                    """SELECT
                            aff_id
                        FROM
                            users
                        WHERE
                            login = %s
                            OR
                            email_address = %s
                    """, (username, email_address,))
                user = await cur.fetchone()
                if user is not None:
                    return False, f"Username {username} is already taken."
            aff_id = None
            while aff_id is None:  # TODO: Maybe use INSERT IGNORE instead.
                aff_id_try = genword(length=4, charset="ascii_50")
                await cur.execute(
                    """
                    SELECT COUNT(*) as cnt
                        FROM affiliate_links al
                        WHERE
                            al.tracking_key = %s
                    """, (aff_id_try,))
                aff_id_exist = await cur.fetchone()
                if aff_id_exist['cnt'] == 0:
                    aff_id = aff_id_try
            password_hash = argon2.using(type='ID').hash(password)
            is_employer = 1 if account_type == 'employer' else 0
            if is_employer:
                await cur.execute(
                    """
                    SELECT COUNT(*) as cnt
                    FROM orgs
                    WHERE
                        org_name = %s
                    """, (company_name,))
                org_name_check = await cur.fetchone()
                if org_name_check['cnt'] != 0:
                    return False, "Company name is already taken. Please choose another."
            try:
                if invited_user is None:
                    await cur.execute("""INSERT INTO
                                            users
                                        SET
                                            login = %s,
                                            password_hash = %s,
                                            aff_id = %s,
                                            gravatar = %s,
                                            email_address = %s,
                                            first_name = %s,
                                            last_name = %s,
                                            mobile_number = %s,
                                            user_level = 2,
                                            is_employer = %s
                                        """,
                                      (username,
                                       password_hash,
                                       aff_id,
                                       email_md5,
                                       email_address,
                                       first_name,
                                       last_name,
                                       mobile_number,
                                       is_employer,))
                else:
                    await cur.execute(
                        """
                        UPDATE
                            users
                        SET
                            login = %s,
                            password_hash = %s,
                            aff_id = %s,
                            gravatar = %s,
                            email_address = %s,
                            mobile_number = %s,
                            user_level = 1,
                            first_name = %s,
                            last_name = %s,
                            is_new_user = 0,
                            is_employer = %s
                        WHERE id = %s
                        """,
                        (username,
                         password_hash,
                         aff_id,
                         email_md5,
                         email_address,
                         mobile_number,
                         first_name,
                         last_name,
                         is_employer,
                         invited_user['id'],))
                await conn.commit()
                user_id = invited_user['id'] if invited_user is not None else cur.lastrowid
                if is_employer and invited_user is None:
                    await cur.execute(
                        """
                        INSERT INTO orgs
                        SET
                            org_name = %s,
                            departments = %s,
                            user_id = %s
                        """, (company_name,
                              ujson.dumps([{
                                  'name': 'management',
                                  'slug': 'management',
                                  'text': 'Management'
                              }]),
                              user_id,))
                    await conn.commit()
                    org_id = cur.lastrowid
                    await cur.execute(
                        """
                        INSERT INTO departments
                        SET org = %s,
                        dept_name = %s,
                        dept_slug = %s
                        """, (org_id, 'management', 'management',))
                    await conn.commit()
                    dept_id = cur.lastrowid
                    await cur.execute(
                        """
                        UPDATE orgs
                        SET departments = %s
                        WHERE id = %s""",
                        (ujson.dumps([{
                            'id': dept_id,
                            'name': 'management',
                            'slug': 'management',
                            'text': 'Management'
                        }]), org_id,))
                    await cur.execute(
                        """
                        UPDATE users
                        SET org = %s,
                        company_name = %s
                        WHERE id = %s
                        """,
                        (org_id, company_name, user_id,))
            except Exception as ex:
                log.exception(ex)
            
            '''await cur.execute(
                """
                INSERT INTO affiliate_links
                SET
                    link_name = %s,
                    landing_page = %s,
                    design = %s,
                    user_id = %s,
                    tracking_key = %s
                """,
                ("Default", "/", 1,
                 user_id, aff_id,))
            await conn.commit()'''
            
            if is_employer:
                await cur.execute("""INSERT INTO
                                        permissions
                                    SET
                                        user_id = %s,
                                        perm_name = 'employer'
                                    """,
                                  (user_id,))
            else:
                await cur.execute("""INSERT INTO
                                        permissions
                                    SET
                                        user_id = %s,
                                        perm_name = 'employee'
                                    """,
                                  (user_id,))
            await cur.execute("""INSERT INTO
                                    permissions
                                SET
                                    user_id = %s, perm_name = 'user'
                                """,
                              (user_id,))
            return True, f"Account {username} registered."
