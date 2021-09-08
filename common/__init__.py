import asyncio
import json
import logging as log
import math
import random
import re
import time
from datetime import date, datetime

import aiomysql
from aiomysql import DictCursor
from mo_dots import Data, from_data, to_data
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client

from globals import ENV

ENV = to_data(ENV)
ENV.URL_PROTO = 'https://' if 'SITE_SSL' in ENV and ENV.SITE_SSL else 'http://'


def site_title(page_name):
    return f"{ENV.SITE_NAME} - {page_name}"


REGEX = {
    'referer': re.compile("^[a-zA-Z0-9/_]+$"),
    'username': re.compile('^[a-zA-Z0-9]+$')
}


def format_cerberus(errors):
    error_key = next(iter(errors))
    return f"{error_key.replace('_', ' ')} {errors[error_key][0]}"


def unix_epoch():
    return int(time.time())


def validate_referer(value):
    if len(value) < 1 or len(value) > 256:
        return False
    return bool(REGEX['referer'].match(value))


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def dumps(o):
    return json.dumps(o, default=json_serial)


def date_to_str(dt):
    return dt.isoformat()


def referer_validator(referer_regex, value):
    if len(value) < 1 or len(value) > 256:
        return False
    return referer_regex.match(value)


def responder_puid():
    return "#s" + str(random.random())


def expector_puid():
    return "#c" + str(random.random())


def send_email(recipient_email, subject, message_html):
    message = Mail(
        from_email=ENV['EMAIL_DEFAULT_SENDER'],
        to_emails=recipient_email,
        subject=subject,
        html_content=message_html)
    try:
        sg = SendGridAPIClient(ENV['EMAIL_SENDGRID_KEY'])
        response = sg.send(message)
        log.debug(response)
    except Exception as ex:
        log.exception(ex)


def send_sms(recipient_phone, message):
    try:
        client = Client(
            ENV['SMS_TWILIO_ACCOUNT_SID'],
            ENV['SMS_TWILIO_AUTH_TOKEN']
        )
        sms_message = client.messages.create(
            body=message,
            from_=ENV['SMS_TWILIO_NUMBER'],
            to=recipient_phone
        )
    except Exception as ex:
        log.exception(ex)


def light_or_dark(color, threshold=127.5):
    """
    Takes a color value (Hex or RGB). Returns
    true if color is light, False if the color
    is dark.
    :param color: Any hex or rgb string.
    :param threshold: light/dark threshold. The deault is usually suitable.
    :return: True if the color is light, False if it's dark.
    """
    if color[:3] == 'rgb':
        color = re.match("/^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d+(?:\.\d+)?))?\)$/", color)
        
        r = color[1]
        g = color[2]
        b = color[3]
    else:
        color = int(re.sub("(.)", r"\1\1" if len(color) < 5 else r"\1", color[1:]), 16)
        r = color >> 16
        g = color >> 8 & 255
        b = color & 255
    hsp = math.sqrt(
        0.299 * (r * r) +
        0.587 * (g * g) +
        0.114 * (b * b)
    )
    return hsp > threshold


def get_between(subject, start, end):
    matches = re.findall(f'{start}(.*){end}', subject)
    return matches if len(matches) else None


def mo_dumps(data):
    return json.dumps(data, default=from_data)


def safe_dumps(_j):
    return json.dumps(_j, default=str)


log_lvl = getattr(log, ENV.SITE_LOG_LEVEL)
log.basicConfig(level=log_lvl)
log.debug(ENV)

departments = [
    {
        "value": 1,
        "name": "executive",
        "avatar": "/images/icons/fap/svgs/regular/briefcase.svg",
        "slug": "executive",
        "bgcolor": "#3A43BA",
        "fa": "briefcase",
        "color": "#000000" if light_or_dark("#3A43BA") else "#FFFFFF"
    },
    {
        "value": 2,
        "name": "upper management",
        "avatar": "/images/icons/fap/svgs/regular/user-tie.svg",
        "slug": "upper-management",
        "bgcolor": "#3BB143",
        "fa": "user-tie",
        "color": "#000000" if light_or_dark("#3BB143") else "#FFFFFF"
    },
    {
        "value": 3,
        "name": "human relations",
        "avatar": "/images/icons/fap/svgs/regular/users.svg",
        "slug": "human-relations",
        "bgcolor": "#012D36",
        "fa": "users",
        "color": "#000000" if light_or_dark("#012D36") else "#FFFFFF"
    },
    {
        "value": 4,
        "name": "sales",
        "avatar": "/images/icons/fap/svgs/regular/dollar-sign.svg",
        "slug": "sales",
        "bgcolor": "#D21502",
        "fa": "dollar-sign",
        "color": "#000000" if light_or_dark("#D21502") else "#FFFFFF"
    },
    {
        "value": 5,
        "name": "marketing",
        "avatar": "/images/icons/fap/svgs/regular/analytics.svg",
        "slug": "marketing",
        "bgcolor": "#A10559",
        "fa": "chart-line",
        "color": "#000000" if light_or_dark("#A10559") else "#FFFFFF"
    },
    {
        "value": 6,
        "name": "customer service",
        "avatar": "/images/icons/fap/svgs/regular/question.svg",
        "slug": "customer-service",
        "bgcolor": "#F14925",
        "fa": "question",
        "color": "#000000" if light_or_dark("#F14925") else "#FFFFFF"
    },
    {
        "value": 7,
        "name": "accounting",
        "avatar": "/images/icons/fap/svgs/regular/plus.svg",
        "slug": "accounting",
        "bgcolor": "#FC8F57",
        "fa": "plus",
        "color": "#000000" if light_or_dark("#FC8F57") else "#FFFFFF"
    },
    {
        "value": 8,
        "name": "security",
        "avatar": "/images/icons/fap/svgs/regular/lock.svg",
        "slug": "security",
        "bgcolor": "#6C1371",
        "fa": "lock",
        "color": "#000000" if light_or_dark("#6C1371") else "#FFFFFF"
    },
    {
        "value": 9,
        "name": "IT",
        "avatar": "/images/icons/fap/svgs/regular/code.svg",
        "slug": "it",
        "bgcolor": "#FFD33A",
        "fa": "code",
        "color": "#000000" if light_or_dark("#FFD33A") else "#FFFFFF"
    }
]


def fmt_cron(cron_txt):
    cron_txt = cron_txt.replace('* minutes', 'minute')
    cron_txt = cron_txt.replace('* hours', 'hour')
    cron_txt = cron_txt.replace('* days', 'day')
    cron_txt = cron_txt.replace('* weeks', 'week')
    cron_txt = cron_txt.replace('* months', 'month')
    return cron_txt.lower()


def strip_nonnumeric(the_str):
    numeric_filter = filter(str.isdigit, the_str)
    return "".join(numeric_filter)


def unique_union(*args):
    return list(set().union(*args))


async def notify_user(app, user_id, title, msg, calling_path="/", icon="grommet-icons:info", seen=0):
    sql_append = ''
    if ENV.ALLOW_DUPE_NOTIFY:
        sql_append = f" AND MINUTE(TIMEDIFF(NOW(), datetime_stamp)) < {ENV.DUPE_BLOCK_MINS} "
    async with app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                f"""
                SELECT COUNT(*) as cnt
                FROM notifications
                WHERE user_id = %s
                AND title = %s
                AND msg = %s
                {sql_append}
                """, (user_id, title, msg,))
            noti_dupes = await cur.fetchone()
            if noti_dupes is not None and noti_dupes['cnt'] > 0:
                log.debug(f"Skippig duplicate notification for user #{user_id} title: {title}, msg: {msg}")
                return False
            else:
                log.debug(f"Notified user #{user_id} of {title}")
                await cur.execute("""
                INSERT INTO notifications
                SET
                    user_id = %s,
                    title = %s,
                    msg = %s,
                    calling_path = %s,
                    icon = %s,
                    seen = %s
                """, (user_id, title, msg, calling_path, icon, seen,))
                await conn.commit()
                return True


_urlfinderregex = re.compile(r'http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}')


def linkify(text, maxlinklength=255):
    def replacewithlink(matchobj):
        url = matchobj.group(0)
        text = str(url)
        if text.startswith('http://'):
            text = text.replace('http://', '', 1)
        elif text.startswith('https://'):
            text = text.replace('https://', '', 1)
        
        if text.startswith('www.'):
            text = text.replace('www.', '', 1)
        
        if len(text) > maxlinklength:
            halflength = maxlinklength / 2
            text = text[0:halflength] + '...' + text[len(text) - halflength:]
        
        return f'<a href="{url}" target="_blank" rel="nofollow">Visit @ Hiyer</a>'
    
    if text is not None and text != '':
        return _urlfinderregex.sub(replacewithlink, text)
    else:
        return ''


async def aiohttp_fakeapp(mysql=True):
    app = Data()
    if mysql:
        loop = asyncio.get_event_loop()
        app['mysql'] = await aiomysql.create_pool(host=ENV.MYSQL_HOSTNAME, port=ENV.MYSQL_PORT,
                                                  user=ENV.MYSQL_USERNAME, password=ENV.MYSQL_PASSWORD,
                                                  db=ENV.MYSQL_DATABASE, loop=loop, autocommit=True)
    return app


async def depts_of_org(org_id, _mysql):
    async with _mysql.acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                """
                SELECT depts.id as id,
                    depts.name COLLATE utf8mb4_bin AS name,
                    depts.slug COLLATE utf8mb4_bin AS slug
                FROM orgs o,
                JSON_TABLE(
                    o.departments -> '$',
                    '$' COLUMNS (
                        NESTED PATH '$[*]' COLUMNS (
                            `id` VARCHAR(64) COLLATE utf8mb4_bin PATH '$.id',
                            name VARCHAR(64) COLLATE utf8mb4_bin PATH '$.name',
                            slug VARCHAR(64) COLLATE utf8mb4_bin PATH '$.slug'
                        )
                    )
                ) AS depts
                WHERE o.id = %s
                UNION DISTINCT
                SELECT d.id as id,
                    d.dept_name as name,
                    d.dept_slug as slug
                FROM departments d
                WHERE org = %s
                """, (org_id, org_id,))
            return await cur.fetchall()


async def org_dept_exists(org_id, dept_slug, _mysql):
    async with _mysql.acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                """
                SELECT DISTINCT org, slug
                FROM (
                         SELECT depts.name COLLATE utf8mb4_bin AS name,
                                depts.slug COLLATE utf8mb4_bin AS slug,
                                o.id COLLATE utf8mb4_bin       AS org
                         FROM orgs o,
                              JSON_TABLE(
                                      o.departments -> '$',
                                      '$' COLUMNS (
                                          NESTED PATH '$[*]' COLUMNS (
                                      name VARCHAR(64) COLLATE utf8mb4_bin PATH '$.name',
                                      slug VARCHAR(64) COLLATE utf8mb4_bin PATH '$.slug'
                                      )
                                          )
                                  ) depts
                                  CROSS JOIN
                              departments d
                         WHERE slug = %s
                     ) res
                WHERE org = %s
                AND slug = %s
                """, (dept_slug, org_id, dept_slug,))
            return not not await cur.fetchone()


def percentage(part, whole):
    if (whole):
        _percentage = 100 * float(part) / float(whole)
        return str(_percentage) + '%'

    return '0%'
