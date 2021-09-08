import asyncio
import json
import random
import time
import uuid
from datetime import datetime

import aiohttp
import aiohttp_csrf
import jwt
import ujson
from aiohttp import WSMsgType, web
from aiojobs.aiohttp import atomic, spawn
from aiomysql import DictCursor
from aioredis.abc import AbcChannel
from aioredis.pubsub import Receiver
from cron_descriptor import CasingTypeEnum, ExpressionDescriptor
from croniter import croniter
from mo_dots import to_data
from passlib import pwd
from passlib.context import CryptContext
from pyprnt import prnt
from switch import Switch

from auth import init_auth
from common import ENV, depts_of_org, fmt_cron, log, mo_dumps, org_dept_exists, responder_puid, safe_dumps, \
    strip_nonnumeric, percentage
from redismod.streams import Streams
from routes.auth import do_register


class WsReply:

    def __init__(self, ws, client_msg):
        self.ws = ws
        self.client_msg = client_msg

    async def reply(self, reply_data):
        #reply_data = to_data(reply_data)
        if '#c' in self.client_msg['puid']:
            new_puid = self.client_msg['puid'].replace('#c', '#s')
        elif '#s' in self.client_msg['puid']:
            new_puid = self.client_msg['puid'].replace('#s', '#c')
        else:
            raise ValueError('Missing puid in message.')
        if 'cmd' in self.client_msg:
            cmd = self.client_msg['cmd']
        elif 'cmd' in reply_data:
            cmd = reply_data['cmd']
        else:
            cmd = 'general_reply'
        success = reply_data['success'] if 'success' in reply_data else False
        # reply_data['puid'] = new_puid  # TODO: Figure out the puid situation
        reply_data['puid'] = self.client_msg['puid']
        reply_data['cmd'] = cmd
        reply_data['success'] = success
        log.debug(f'Sending Reply: {reply_data}')
        await self.ws.send_json(reply_data, dumps=safe_dumps)


@atomic
async def close_ws_atomic(request, ws):
    log.debug(f'ws connection closed with exception {ws.exception()}')
    request.app["websockets"].remove(ws)


# section: sub_reader
async def sub_reader(_redis, ws, _red_recv, _auth):  # TODO: Refactor func name
    channels = (_red_recv.channel('globe:surveys'),)
    if _auth.logged_in:
        channels += (_red_recv.channel(f'user:{_auth.id}'),)
    await _redis.subscribe(channels)  # _red_recv.channel('globe:surveys')
    # section sub_reader
    log.debug("Activating sub reader.")
    async for channel, msg in _red_recv.iter(encoding="utf-8"):
        log.debug("Got {!r} in channel {!r}".format(msg, channel))
        assert isinstance(channel, AbcChannel)
        ws.send_json(msg)


# section: listen_to_redis
async def listen_to_redis(app: web.Application, channel="globe:surveys") -> None:
    log.debug('Entered listen_to_redis')
    ch = None
    try:
        ch, *_ = await app['redis'].subscribe(channel)
        async for msg in ch.iter(encoding="utf-8"):
            ch_name = ch.name
            if hasattr(ch_name, 'decode'):
                ch_name = ch_name.decode()
            if hasattr(msg, 'decode'):
                msg = msg.decode()
            # log.debug(msg)
            msg = ujson.loads(msg)
            ch_spl = ch_name.split(":")
            if len(ch_spl) == 2:
                if ch_spl[0] == "globe":
                    # Forward message to all connected websockets:
                    for ws in app["websockets"]:
                        await ws.send_json({
                            'cmd': ch_name,
                            'puid': responder_puid(),  # expector_puid(),
                            'data': msg,
                            'succcess': True
                        })
                elif ch_spl[0] == "user":
                    user_id = ch_spl[1]
                    ws = app["user_websockets"][user_id]
                    await ws.send_json({
                        'cmd': ch_name,
                        'puid': responder_puid(),  # expector_puid(),
                        'data': msg,
                        'succcess': True
                    })
    except asyncio.CancelledError:
        log.debug('Redis task got cancelled error.')
        pass
    except Exception as ex:
        log.exception(ex)
    finally:
        log.debug("Cancel Redis listener: close connection...")
        if ch is not None:
            await app['redis'].unsubscribe(ch.name)
        # await app['redis'].quit()
        log.debug("Redis connection closed.")


# section: websocket_handler
@aiohttp_csrf.csrf_exempt
async def websocket_handler(request):
    # section websocket_handler
    log.info("Entered WS...")
    auth = await init_auth(request)
    #alerter = Alert(web, session)
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    request.app['skip_disconnect'] = False
    # section gcache
    recv_id = None
    while recv_id is None:
        new_recv_id = str(random.random())
        if new_recv_id not in request.app['redis_receivers']:
            recv_id = new_recv_id
            request.app['redis_receivers'][recv_id] = Receiver(
                loop=asyncio.get_running_loop())

    # red_recv = Receiver(loop=asyncio.get_running_loop())
    # asyncio.ensure_future(sub_reader(request.app['redis'], ws, request.app['redis_receivers'][recv_id], auth))
    if auth.logged_in:
        ws_id = auth.user_id
        stream = Streams(request.app['redis'], ws, log)
        await spawn(request, listen_to_redis(request.app, f"user:{auth.user_id}"))
        '''asyncio.gather(asyncio.create_task(
            listen_to_redis(request.app,
                            f"user:{auth.user_id}")
        ))'''
        # async with request.app[f'{client_class}_ws_lock']:
        request.app["user_websockets"][ws_id] = ws
    """else:
        async with request.app[f'{client_class}_ws_lock']:
        ws_id = len(request.app[f"{client_class}_websockets"]) + 1
        request.app[f"{client_class}_websockets"][ws_id] = ws"""
    request.app["websockets"].append(ws)

    try:
        async for msg in ws:
            # section ws loop
            if msg.type == WSMsgType.TEXT:
                data = msg.data
                try:
                    j = ujson.loads(data)
                    log.debug('from client:' + ujson.dumps(j))
                    j = to_data(j)
                    wsr = WsReply(ws, j)
                    if 'cmd' in j:
                        with Switch(j.cmd) as case:

                            if case('ping'):
                                await wsr.reply({
                                    'cmd': 'pong',
                                    'success': True
                                })

                            if case('rm_user'):
                                _auth = await init_auth(request, protect=True, permission='admin')
                                await ws.send_json(_auth)
                                await wsr.reply(_auth)

                            if case('add_dept'):
                                if 'dept' not in j:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': 'Missing department.'
                                    })
                                    continue
                                if await org_dept_exists(auth.org, j.dept.slug, request.app['mysql']):
                                    await wsr.reply({
                                        'success': False,
                                        'msg': f'Org already has department "{j.dept.name}"'
                                    })
                                    continue
                                await request.app["tags"].add(j.dept.slug)
                                log.debug(f"Departments in WS: {[t.decode() for t in await request.app['redis'].smembers('depts')]}")
                                async with request.app['mysql'].acquire() as conn:
                                    async with conn.cursor(DictCursor) as cur:
                                        depts = await depts_of_org(auth.org, request.app['mysql'])
                                        depts_table_flat = [
                                            d['slug'] for d in depts] if depts is not None else []
                                        if j.dept.slug in depts_table_flat:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': f'Org already has department "{j.dept.name}"'
                                            })
                                            continue
                                        if j.dept.slug not in request.app['dept_list']:
                                            request.app['dept_list'].append(
                                                j.dept.slug)
                                        await cur.execute(
                                            """
                                            INSERT INTO departments
                                            SET
                                                dept_name = %s,
                                                org = %s,
                                                dept_slug = %s
                                            """, (j.dept.name,
                                                  auth.org,
                                                  j.dept.slug,))
                                        await conn.commit()
                                        dept_id = cur.lastrowid
                                        depts_table_flat.append(j.dept.slug)
                                        depts.append({
                                            'id': dept_id,
                                            'name': j.dept.name,
                                            'slug': j.dept.slug,
                                            'text': j.dept.name[0].capitalize() + j.dept.name[1:]
                                        })
                                        await cur.execute(
                                            """
                                            UPDATE orgs
                                            SET departments = %s
                                            WHERE id = %s
                                            """, (ujson.dumps(depts),
                                                  auth.org,))
                                        await conn.commit()

                                        await wsr.reply({
                                            'success': True,
                                            'msg': f'Added department "{j.dept.name}" to organization.'
                                        })
                                        continue

                            if case('icons') and 'icon' in j:
                                # log.debug('Icon request for:', j.icon)
                                if j.icon in request.app["icons"]:
                                    icons = request.app["icons"][j.icon]
                                else:
                                    icons = None
                                await wsr.reply({
                                    'success': True,
                                    'msg': f"Got icon: {j.icon}",
                                    'icons': icons
                                })

                            if case('icon_insta') and 'icon' in j:
                                # log.debug('Icon request for:', j.icon)

                                def slug(_x):
                                    return _x.replace(' ', '-')

                                res = []
                                q = j.icon if 'icon' in j and len(
                                    j.icon) else None
                                if q is None:
                                    await ws.send_json({
                                        'success': False,
                                        "puid": j.puid if 'puid' in j else "00",
                                        'msg': f"Missing `icon` name."
                                    }, dumps=mo_dumps)
                                    continue
                                if len(q) > 1 and q in request.app['icons']:
                                    libs = request.app['icons'][q].libs
                                    ico_groups = []
                                    for lib in libs:
                                        ico_groups.append([
                                            {'name': slug, 'value': slug,
                                                'slug': slug, 'prefix': lib.prefix}
                                            for slug, icon_obj in lib.icons.items()
                                            if q == slug
                                        ])
                                        for el in sum(ico_groups, []):
                                            res.append(el)
                                elif q[0] in request.app["ico_dex"]:
                                    libs = request.app["icons"][q[0]].libs
                                    ico_groups = []
                                    for lib in libs:
                                        ico_groups.append([
                                            {'name': slug, 'value': slug,
                                                'slug': slug, 'prefix': lib.prefix}
                                            for slug, icon_obj in lib.icons.items()
                                            if q[0] == slug[0]
                                        ])
                                        for el in sum(ico_groups, []):
                                            res.append(el)
                                # icons = [{'value': slug(x), 'name': slug(x), 'avatar': None, 'slug': slug(x), 'bgcolor': '#FFFFFF', 'fa': None} for x in [y.icons for y in request.app['icons'].libs] if re.q(j.icon, x)]
                                await wsr.reply({
                                    'success': True,
                                    'msg': f"Result for query: {q}",
                                    'icons': res
                                })

                            if case('submit_answer'):
                                if 'answer_json' not in j:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': f"Missing survey answer."
                                    })
                                    continue
                                if 'survey_uuid' not in j:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': f"Missing survey ID."
                                    })
                                    continue

                                async with request.app['mysql'].acquire() as conn:
                                    async with conn.cursor(DictCursor) as cur:
                                        await cur.execute(
                                            """
                                            SELECT * FROM surveys
                                            WHERE
                                                survey_uuid = %s
                                            """, (j.survey_uuid,))
                                        sfound = await cur.fetchone()
                                        if sfound is None:  # FIXME: validate by user's permission to the question.
                                            await wsr.reply({
                                                'success': False,
                                                'msg': "Survey not found."
                                            })
                                            continue
                                        if 'qid' in j:
                                            try:
                                                j.qid = int(j.qid)
                                            except Exception as ex:
                                                await wsr.reply({
                                                    'success': False,
                                                    'msg': "Invalid question ID."
                                                })
                                                log.exception(ex)
                                                continue
                                        j.qid = int(
                                            j.qid) if 'qid' in j else None
                                        await cur.execute(
                                            """
                                            INSERT INTO answers
                                            SET
                                                answer_json = %s,
                                                survey_uuid = %s,
                                                user_id = %s,
                                                qid = %s
                                            """, (mo_dumps(j.answer_json),
                                                  j.survey_uuid,
                                                  _auth.user_id,
                                                  j.qid,))
                                        await wsr.reply({
                                            'success': True,
                                            'msg': f"Survey answer(s) submitted."
                                        })
                                        continue

                            if case('token'):
                                try:
                                    # TODO: Maybe should protect
                                    _auth = await init_auth(request, protect=False)
                                    if _auth.logged_in:
                                        await ws.send_json({
                                            'cmd': 'token',
                                            'data': jwt.encode(  # web.json_response(
                                                {
                                                    "username": _auth.username,
                                                    "scopes": [f"username:{_auth.username}"]
                                                }, ENV.JWT_SECRET),
                                            'success': True,
                                            "puid": j.puid if 'puid' in j else "00"
                                        })
                                    else:
                                        await wsr.reply({
                                            'success': False,
                                            'data': j
                                        })
                                except web.HTTPUnauthorized as ex:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': 'Unauthorized'
                                    })

                            if case('add_org'):
                                try:
                                    _auth = await init_auth(request, protect=True, permission='user')
                                    if _auth.logged_in:
                                        async with request.app['mysql'].acquire() as conn:
                                            async with conn.cursor(DictCursor) as cur:
                                                await cur.execute(
                                                    """
                                                    SELECT * FROM orgs
                                                    WHERE
                                                        org_name = %s
                                                    """, (j.name,))
                                                dupe_org = await cur.fetchone()
                                                if dupe_org is not None:
                                                    await ws.send_json({
                                                        'success': False,
                                                        'data': j,
                                                        "puid": j.puid if 'puid' in j else "00"
                                                    })
                                                    break
                                                await cur.execute(
                                                    """
                                                    INSERT INTO orgs
                                                    SET
                                                        org_name = %s,
                                                        departments = %s,
                                                        user_id = %s
                                                    """, (j.name,
                                                          mo_dumps(
                                                              j.departments),
                                                          _auth.user_id))
                                                await ws.send_json({
                                                    'success': True,
                                                    'msg': 'Organization Added',
                                                    "puid": j.puid if 'puid' in j else "00"
                                                })
                                                break
                                    else:
                                        await ws.send_json({
                                            'success': False,
                                            'data': j,
                                            "puid": j.puid if 'puid' in j else "00"
                                        })
                                except web.HTTPUnauthorized as ex:
                                    await ws.send_json({
                                        'success': False,
                                        'data': j,
                                        'error': str(ex),
                                        "puid": j.puid if 'puid' in j else "00"
                                    })

                            if case('set_org_name'):
                                try:
                                    _auth = await init_auth(request, protect=True, permission='user')
                                    if not _auth.logged_in:
                                        await wsr.reply({
                                            'success': False,
                                            'msg': 'One must login to change the org name.'
                                        })
                                        continue
                                    if 'org_name' not in j or len(j.org_name) == 0:
                                        await wsr.reply({
                                            'success': False,
                                            'msg': 'Org name cannot be empty.'
                                        })
                                        continue
                                    async with request.app['mysql'].acquire() as conn:
                                        async with conn.cursor(DictCursor) as cur:
                                            await cur.execute(
                                                """
                                                SELECT COUNT(*) as cnt
                                                FROM orgs
                                                WHERE
                                                    user_id = %s
                                                """, (_auth.user_id,))
                                            user_has_org = await cur.fetchone()
                                            if user_has_org is None or user_has_org['cnt'] == 0:
                                                await cur.execute(
                                                    """
                                                    INSERT INTO orgs
                                                    SET
                                                        org_name = %s,
                                                        departments = %s,
                                                        user_id = %s
                                                    """, (j.name,
                                                          ujson.dumps({
                                                              'id': 0,
                                                              'name': 'departments',
                                                              'slug': 'departments',
                                                              'text': 'Departments'
                                                          }),
                                                          _auth.user_id))
                                            else:
                                                await cur.execute(
                                                    """
                                                    UPDATE orgs
                                                    SET org_name = %s
                                                    WHERE
                                                        id = %s
                                                    """, (j.org_name, _auth.org,))
                                            await wsr.reply({
                                                'success': True,
                                                'msg': 'Org name saved.'
                                            })
                                            continue
                                except web.HTTPUnauthorized as ex:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': 'One must login to change the org name.'
                                    })
                                    continue

                            if case('get_general_data'):
                                questions = None
                                answers = None
                                notifications = []
                                org_answers = None
                                crons = None
                                surveys_to_take = []
                                db_depts = None
                                try:
                                    async with request.app['mysql'].acquire() as conn:
                                        async with conn.cursor(DictCursor) as cur:
                                            await cur.execute(
                                                """
                                                SELECT * FROM admin_settings
                                                WHERE
                                                    setting = 'tag_weight'
                                                    or
                                                    setting = 'dept_weight'
                                                """)
                                            admin_settings = await cur.fetchall()
                                            await cur.execute("SELECT * FROM categories")
                                            categories = await cur.fetchall()
                                            _auth = await init_auth(request, protect=True, permission='user')
                                            if _auth.logged_in:
                                                if _auth['is_employer']:
                                                    # TODO: Joins
                                                    await cur.execute(
                                                        """
                                                        SELECT sq.id as id,
                                                        sq.org as org,
                                                        sq.question as question,
                                                        sq.cat as cat,
                                                        s.survey_title as survey_title,
                                                        s.id as survey_id
                                                        FROM survey_questions sq
                                                        LEFT JOIN surveys s
                                                        ON s.id = sq.survey_id
                                                        WHERE
                                                              sq.org = %s
                                                        ORDER BY sq.survey_id, sq.id
                                                        """, (auth['org'],))
                                                    questions = await cur.fetchall()
                                                    questions = to_data(questions) if questions is not None and len(
                                                        questions) > 0 else []
                                                    questions_tagify = []
                                                    survey_counts = {}
                                                    for question in questions:
                                                        survey_counts[question.survey_id] = survey_counts[question.survey_id] + \
                                                            1 if question.survey_id in survey_counts else 1
                                                        questions_tagify.append({
                                                            'id': question.id,
                                                            'value': question.id,
                                                            'question': ujson.loads(question.question),
                                                            'cat': question.cat,
                                                            'survey_title': question.survey_title,
                                                            'survey_id': question.survey_id,
                                                            'qnum': survey_counts[question.survey_id],
                                                            'qnum_txt': f"#{survey_counts[question.survey_id]}",
                                                            'name': f"{question.survey_title} - Q#{survey_counts[question.survey_id]}"
                                                        })
                                                    questions = questions_tagify

                                                    await cur.execute(
                                                        """
                                                        SELECT *
                                                        FROM answers a
                                                        JOIN users u
                                                        ON a.user_id = u.id
                                                        WHERE a.user_id = %s
                                                        """, (_auth['user_id'],))
                                                    org_answers = await cur.fetchall()
                                                    log.debug(
                                                        f'org_answers: {org_answers}')
                                                    users_answered_qs = [
                                                        a['qid'] for a in org_answers]
                                                    questions = [
                                                        q for q in questions if q['id'] not in users_answered_qs]
                                                    # TODO: Return user's org's crons?
                                                    await cur.execute(
                                                        """
                                                        SELECT c.*,
                                                        cats.cat_name
                                                        FROM crons c
                                                        JOIN categories cats
                                                        ON cats.id = c.cat
                                                        WHERE user_id = %s
                                                        ORDER BY id DESC
                                                        """, (_auth['user_id'],))
                                                    crons = await cur.fetchall()
                                                    log.debug(
                                                        f'crons: {crons}')
                                                    if crons is not None:
                                                        for cron in crons:
                                                            questions_cnt = 0
                                                            surveys_cnt = 0
                                                            response_rate = 0
                                                            try:
                                                                cron['questions'] = ujson.loads(
                                                                    cron['questions'])
                                                                questions_cnt = len(
                                                                    cron['questions'])
                                                            except:
                                                                cron['questions'] = [
                                                                ]
                                                            try:
                                                                cron['surveys'] = ujson.loads(
                                                                    cron['surveys'])
                                                                if len(cron['surveys']) > 0:
                                                                    for this_survey_uuid in cron['surveys']:
                                                                        await cur.execute(
                                                                            """
                                                                            SELECT COUNT(sq.id) as questions_cnt
                                                                            FROM surveys s
                                                                            LEFT JOIN survey_questions sq
                                                                            ON s.id = sq.survey_id
                                                                            WHERE s.survey_uuid = %s
                                                                            """, (this_survey_uuid,))
                                                                        sqs_cnt = await cur.fetchone()
                                                                        questions_cnt += sqs_cnt['questions_cnt'] if sqs_cnt is not None else 0
                                                            except:
                                                                cron['surveys'] = [
                                                                ]
                                                            await cur.execute(
                                                                """
                                                                SELECT COUNT(si.id) as invites_cnt,
                                                                COUNT(si.answered = 1 or null) as answers_cnt
                                                                FROM survey_invites si
                                                                WHERE si.cron_id = %s
                                                                """, cron['id'],)
                                                            answers = await cur.fetchone()
                                                            cron['invites_cnt'] = answers['invites_cnt']
                                                            cron['answers_cnt'] = answers['answers_cnt']
                                                            cron['surveys_cnt'] = surveys_cnt
                                                            cron['questions_cnt'] = questions_cnt
                                                            cron['response_rate'] = percentage(
                                                                answers['answers_cnt'], answers['invites_cnt'])
                                                elif _auth['logged_in']:
                                                    # FIXME: Use survey_invites
                                                    '''await cur.execute(
                                                        f"""
                                                        SELECT c.depts, s.survey_uuid, c.runs, c.id as cron_id, s.org, c.questions
                                                        FROM surveys s
                                                                 JOIN crons c
                                                                      ON (JSON_SEARCH(c.surveys, 'all', s.survey_uuid) IS NOT NULL)
                                                                      OR (JSON_LENGTH(c.questions) > 0)
                                                        WHERE c.start_date < NOW()
                                                          AND c.end_date > NOW()
                                                        """)'''
                                                    await cur.execute(
                                                        """
                                                        SELECT *
                                                        FROM surveys s
                                                                 JOIN crons c
                                                                      ON (JSON_SEARCH(c.surveys, 'all', s.survey_uuid) IS NOT NULL)
                                                                      OR (JSON_LENGTH(c.questions) > 0)
                                                                LEFT JOIN answers a
                                                                    ON s.survey_uuid = a.survey_uuid
                                                        WHERE c.org = %s
                                                          AND a.id IS NULL
                                                          AND JSON_SEARCH(c.depts, 'all', %s) IS NOT NULL
                                                          AND c.start_date < NOW()
                                                          AND c.end_date > NOW()
                                                        GROUP BY s.id
                                                        ORDER BY s.id
                                                        """, (_auth.org, _auth.dept,))
                                                    surveys_to_take = await cur.fetchall()
                                                    await cur.execute(
                                                        """
                                                        SELECT * FROM questions
                                                        WHERE
                                                        org = %s
                                                        AND
                                                        (dept1 = %s or dept2 = %s or dept3 = %s)
                                                        """, (_auth['org'], _auth['dept'], _auth['dept'],
                                                              _auth['dept'],))
                                                    questions = await cur.fetchall()
                                                    await cur.execute(
                                                        """
                                                        SELECT * FROM answers
                                                        WHERE
                                                        user_id = %s
                                                        """, (_auth['user_id'],))
                                                    answers = await cur.fetchall()
                                                    questions = [{
                                                        'id': _q.id,
                                                        'question': _q.question,
                                                        'timestamp': _q.datetime_stamp,
                                                        'icon': {
                                                            'prefix': _q.icon_prefix,
                                                            'icon': _q.icon,
                                                            'color': _q.icon_color
                                                        },
                                                        'depts': [d for d in [_q.dept1, _q.dept2, _q.dept3] if d is not None],
                                                        'tags': [t for t in [_q.tag1, _q.tag2, _q.tag3] if t is not None],
                                                        'options': [o for o in [_q.choice1, _q.choice2, _q.choice3,
                                                                                _q.choice4, _q.choice5] if o is not None]
                                                    } for _q in to_data(questions)]
                                                    users_answered_qs = [
                                                        a['qid'] for a in answers]
                                                    questions = [q for q in questions if
                                                                 q['id'] not in users_answered_qs]
                                                if _auth['logged_in']:
                                                    await cur.execute(
                                                        """
                                                        SELECT
                                                            COUNT(s.id) as survey_cnt,
                                                            COUNT(a.id) as answer_cnt
                                                        FROM surveys s
                                                        JOIN answers a
                                                        ON
                                                            s.survey_uuid = a.survey_uuid
                                                            AND
                                                            a.user_id = %s
                                                        """, (_auth.user_id,)
                                                    )
                                                    counts = await cur.fetchone()
                                                    await cur.execute(
                                                        """
                                                        SELECT * FROM notifications
                                                        WHERE
                                                            user_id = %s
                                                            AND
                                                            seen = 0
                                                            LIMIT 5
                                                        """, (_auth.user_id,))
                                                    notifications = await cur.fetchall()
                                                await cur.execute(
                                                    """
                                                    SELECT org_name, JSON_UNQUOTE(departments) as departments
                                                    FROM orgs
                                                    WHERE
                                                        id = %s
                                                    """, (auth.org,))
                                                orgs = await cur.fetchall()
                                                depts = []
                                                for org in orgs:
                                                    if org['departments'] is not None and len(org['departments']) > 0:
                                                        org['departments'] = ujson.loads(
                                                            org['departments'])
                                                        [depts.append(
                                                            d) for d in org['departments']]
                                                creator_cache = to_data(
                                                    request.app['creator_cache'])
                                                # TODO: move this ln to beginning of ws loop
                                                uid_str = f"{str(_auth.user_id)}"
                                                if uid_str not in creator_cache:
                                                    creator_cache[uid_str]['saves'] = {
                                                    }
                                                await wsr.reply({
                                                    'success': True,
                                                    'token': jwt.encode({
                                                        "username": _auth.username,
                                                        "scopes": [f"username:{_auth.username}"]
                                                    }, ENV.JWT_SECRET),
                                                    'questions': questions,
                                                    'answers': answers,
                                                    'notifications': notifications,
                                                    'admin_settings': admin_settings,
                                                    'orgs': orgs,
                                                    # ast.literal_eval(json.loads(mo_dumps(crons))),
                                                    'crons': crons,
                                                    'depts': depts,
                                                    'cats': categories,
                                                    'draft_cache': creator_cache[uid_str]['draft'] if uid_str in request.app['creator_cache'] else None,
                                                    'saved_surveys': [
                                                        {k: v} for k, v in request.app['creator_cache'][uid_str]['saves'].items()
                                                    ],
                                                    'surveys_to_take': surveys_to_take,
                                                    'count': {
                                                        'surveys': counts['survey_cnt'] or 0,
                                                        'answers': counts['answer_cnt'] or 0
                                                    }
                                                })
                                            else:
                                                pass  # TODO: Send data for guests
                                            continue
                                except Exception as ex:
                                    log.exception(ex)

                            if case('add_question'):
                                try:
                                    _auth = await init_auth(request, protect=True, permission='user')
                                    if _auth.logged_in:
                                        # TODO: Proper validators
                                        if 'question' not in j or len(j.question) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Questions cannot be empty.'
                                            })
                                        if 'icon' not in j.question or len(j.question.icon) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Icon cannot be empty.'
                                            })
                                        if 'tags' not in j.question or len(j.question.tags) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Tags cannot be empty.'
                                            })
                                        if 'departments' not in j.question or len(j.question.departments) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Departments cannot be empty.'
                                            })
                                        if 'choices' not in j.question or len(j.question.choices) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Questions need at least one choice.'
                                            })

                                        choices = j.question.choices

                                        tags = to_data(
                                            ujson.loads(j.question.tags))
                                        depts = to_data(ujson.loads(
                                            j.question.departments))
                                        async with request.app['mysql'].acquire() as conn:
                                            async with conn.cursor(DictCursor) as cur:
                                                await cur.execute(
                                                    """
                                                    SELECT * FROM questions
                                                    WHERE
                                                        question = %s
                                                        AND
                                                        user_id = %s
                                                    """, (j.question.question,
                                                          _auth['user_id'],))
                                                dupe_q = await cur.fetchone()
                                                if dupe_q is not None:
                                                    await wsr.reply({
                                                        'success': False,
                                                        'msg': 'This question already exists.'
                                                    })
                                                    continue
                                                await cur.execute(
                                                    """
                                                    INSERT INTO questions
                                                    SET
                                                        question = %s,
                                                        user_id = %s,
                                                        icon_prefix = %s,
                                                        icon = %s,
                                                        icon_color = %s,
                                                        dept1 = %s, dept2 = %s, dept3 = %s,
                                                        tag1 = %s, tag2 = %s, tag3 = %s,
                                                        choice1 = %s, choice2 = %s, choice3 = %s,
                                                        choice4 = %s, choice5 = %s
                                                    """, (j.question.question,
                                                          _auth['user_id'],
                                                          j.question.icon_prefix,
                                                          j.question.icon,
                                                          j.question.icon_color,
                                                          depts[0].value if len(
                                                              depts) >= 1 else 'all',
                                                          depts[1].value if len(
                                                              depts) >= 2 else None,
                                                          depts[2].value if len(
                                                              depts) >= 3 else None,
                                                          tags[0].value if len(
                                                              tags) >= 1 else None,
                                                          tags[1].value if len(
                                                              tags) >= 2 else None,
                                                          tags[2].value if len(
                                                              tags) >= 3 else None,
                                                          choices[0] if len(
                                                              choices) == 1 else None,
                                                          choices[1] if len(
                                                              choices) == 2 else None,
                                                          choices[2] if len(
                                                              choices) == 3 else None,
                                                          choices[3] if len(
                                                              choices) == 4 else None,
                                                          choices[4] if len(choices) == 5 else None,))
                                                if 'choices' in j.question:
                                                    await cur.execute(
                                                        """
                                                        INSERT INTO multichoice
                                                        SET
                                                            question = %s,
                                                            user_id = %s,
                                                            icon_prefix = %s,
                                                            icon = %s,
                                                            icon_color = %s,
                                                            dept1 = %s, dept2 = %s, dept3 = %s,
                                                            tag1 = %s, tag2 = %s, tag3 = %s
                                                        """, (j.question.question,
                                                              _auth['user_id'],
                                                              j.question.icon_prefix,
                                                              j.question.icon,
                                                              j.question.icon_color,
                                                              depts[0].value if len(
                                                                  depts) >= 1 else 'all',
                                                              depts[1].value if len(
                                                                  depts) >= 2 else None,
                                                              depts[2].value if len(
                                                                  depts) >= 3 else None,
                                                              tags[0].value if len(
                                                                  tags) >= 1 else None,
                                                              tags[1].value if len(
                                                                  tags) >= 2 else None,
                                                              tags[2].value if len(tags) >= 3 else None,))
                                                await ws.send_json({
                                                    'success': True,
                                                    'msg': 'Question added',
                                                    "puid": j.puid if 'puid' in j else "00"
                                                })
                                                continue
                                    else:
                                        await ws.send_json({
                                            'success': False,
                                            'data': j,
                                            "puid": j.puid if 'puid' in j else "00"
                                        })
                                except web.HTTPUnauthorized as ex:
                                    await ws.send_json({
                                        'success': False,
                                        'data': j,
                                        'error': str(ex),
                                        "puid": j.puid if 'puid' in j else "00"
                                    })

                            if case('add_cron'):
                                try:
                                    _auth = await init_auth(request, protect=True, permission='user')
                                    if _auth.logged_in:
                                        # TODO: Proper validators
                                        if 'when_send' not in j or len(j.when_send) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'No send time specified.'
                                            })
                                        if 'tags' not in j or len(j.tags) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Tags cannot be empty.'
                                            })
                                        if 'departments' not in j or len(j.departments) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Departments cannot be empty.'
                                            })
                                        tags = to_data(ujson.loads(j.tags))
                                        depts = to_data(
                                            ujson.loads(j.departments))
                                        cron_date = croniter(
                                            j.when_send, datetime.now())
                                        async with request.app['mysql'].acquire() as conn:
                                            async with conn.cursor(DictCursor) as cur:
                                                await cur.execute(
                                                    """
                                                    INSERT INTO crons
                                                    SET
                                                        tags = %s,
                                                        depts = %s,
                                                        when_send = %s,
                                                        user_id = %s,
                                                        org = %s
                                                    """, (safe_dumps(j.tags),
                                                          safe_dumps(j.depts),
                                                          str(j.when_send),
                                                          _auth['user_id'],
                                                          _auth.org,))
                                                await ws.send_json({
                                                    'success': True,
                                                    'msg': 'Survey questions scheduled.',
                                                    "puid": j.puid if 'puid' in j else "00"
                                                })
                                                continue
                                    else:
                                        await ws.send_json({
                                            'success': False,
                                            'data': j,
                                            "puid": j.puid if 'puid' in j else "00"
                                        })
                                except web.HTTPUnauthorized as ex:
                                    await ws.send_json({
                                        'success': False,
                                        'data': j,
                                        'error': str(ex),
                                        "puid": j.puid if 'puid' in j else "00"
                                    })

                            if case('save_survey'):
                                try:
                                    _auth = await init_auth(request, protect=True, permission='user')
                                    if not _auth.logged_in:
                                        await wsr.reply({
                                            'success': False,
                                            'msg': 'Not logged in.'
                                        })
                                        continue
                                    if 'survey_txt' not in j or len(j.survey_txt) < 1:
                                        await wsr.reply({
                                            'success': False,
                                            'msg': 'Survey save data was empty.'
                                        })
                                        continue
                                    survey = to_data(json.loads(j.survey_txt))
                                    if 'cat' not in survey or ('cat' in survey and len(survey.cat) == 0):
                                        await wsr.reply({
                                            'success': False,
                                            'msg': 'Survey category must be set.'
                                        })
                                        # TODO: Make new function wsr.qreply (quit reply to include continue)
                                        continue

                                    save_type = "draft"
                                    survey_id = str(
                                        uuid.uuid4()).replace('-', '')
                                    if 'title' in survey and len(survey['title']) > 0:
                                        if f"{_auth.user_id}" not in request.app['creator_cache']:
                                            request.app['creator_cache'][f"{_auth.user_id}"] = {
                                                'saves': {},
                                                'draft': ''
                                            }
                                        request.app['creator_cache'][f"{_auth.user_id}"]['saves'][survey_id] = {
                                            'id': survey_id,
                                            'cat': survey.cat,
                                            'title': survey['title'],
                                            'json': survey
                                        }
                                        save_type = ''
                                    request.app['creator_cache'][f"{_auth.user_id}"]['draft'] = j.survey_txt

                                    async with request.app['mysql'].acquire() as conn:
                                        async with conn.cursor(DictCursor) as cur:
                                            await cur.execute("""
                                            SELECT
                                                id
                                            FROM
                                                surveys
                                            WHERE
                                                user_id = %s AND survey_uuid = %s
                                            """, (auth['user_id'], survey_id,))
                                            saved_survey = await cur.fetchone()
                                            sid = saved_survey['id'] if saved_survey is not None else None
                                            if saved_survey is not None:
                                                await cur.execute(
                                                    """
                                                    UPDATE surveys
                                                    SET
                                                        org = %s,
                                                        survey_json = %s,
                                                        survey_uuid = %s,
                                                        survey_title = %s,
                                                        cat = %s
                                                    WHERE
                                                        id = %s and survey_uuid = %s and user_id = %s
                                                    """, (auth.org,
                                                          safe_dumps(survey),
                                                          survey_id,
                                                          survey['title'],
                                                          sid,
                                                          survey_id,
                                                          auth.user_id,
                                                          survey.cat))
                                            else:
                                                await cur.execute(
                                                    """
                                                    INSERT INTO surveys
                                                    SET
                                                        org = %s,
                                                        user_id = %s,
                                                        survey_json = %s,
                                                        survey_uuid = %s,
                                                        survey_title = %s,
                                                        cat = %s
                                                    """, (_auth.org,
                                                          _auth.user_id,
                                                          safe_dumps(survey),
                                                          survey_id,
                                                          survey.title,
                                                          survey.cat,))
                                                await conn.commit()
                                                sid = cur.lastrowid
                                            prnt(survey)
                                            survey = to_data(survey)
                                            for page in survey.pages:
                                                qid = 0
                                                for question in page.elements:
                                                    qid += 1
                                                    question_cat = question.cat if 'cat' in question else survey.cat
                                                    await cur.execute(
                                                        """
                                                        SELECT COUNT(*) as cnt
                                                        FROM survey_questions
                                                        WHERE survey_id = %s
                                                        AND question = %s
                                                        """, (sid, question,))
                                                    question_dupe_check = await cur.fetchone()
                                                    if question_dupe_check['cnt'] == 0:
                                                        await cur.execute(
                                                            """
                                                            INSERT INTO survey_questions
                                                            SET survey_id = %s,
                                                                question = %s,
                                                                org = %s,
                                                                cat = %s,
                                                                qid = %s
                                                            """, (sid,
                                                                  mo_dumps(
                                                                      question),
                                                                  auth.org,
                                                                  question_cat,
                                                                  qid,))  # FIXME: Add cat = %s
                                                        await conn.commit()
                                                    else:
                                                        await cur.execute(
                                                            """
                                                            UPDATE survey_questions
                                                            SET question = %s,
                                                                cat = %s
                                                            WHERE survey_id = %s
                                                            """, (mo_dumps(question),
                                                                  question_cat,
                                                                  sid,))
                                                        await conn.commit()
                                            await wsr.reply({
                                                'success': True,
                                                'msg': 'Survey saved.'
                                            })
                                            continue
                                    await wsr.reply({
                                        'success': True,
                                        'msg': f'Survey {save_type} saved.',
                                        'survey_id': survey_id
                                    })
                                    continue

                                except web.HTTPUnauthorized as ex:
                                    log.debug(ex)
                                    await wsr.reply({
                                        'success': False,
                                        'msg': 'Action not authorized.'
                                    })

                            if case('schedule_survey'):
                                try:
                                    _auth = await init_auth(request, protect=True, permission='user')
                                    if _auth.logged_in:
                                        # TODO: Proper validators
                                        if 'title' not in j or len(j.title) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Survey title not speficied.'
                                            })
                                            continue
                                        if 'department' not in j or len(j.department) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'No departments specified.'
                                            })
                                            continue
                                        if 'category' not in j or len(j.category) < 1:
                                            try:
                                                j.category = int(j.category)
                                            except ValueError:
                                                await wsr.reply({
                                                    'success': False,
                                                    'msg': 'Invalid category specified.'
                                                })
                                                continue
                                        if 'weekly' not in j or len(j.weekly) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Weekly date not specified.'
                                            })
                                            continue
                                        if 'send_at' not in j or len(j.send_at) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Send time not speficied.'
                                            })
                                            continue
                                        if 'order' not in j:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Order not specified.'
                                            })
                                            continue
                                        if 'start_date' not in j or len(j.start_date) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Start date not speficied.'
                                            })
                                            continue
                                        start_date = time.strptime(
                                            j.start_date, "%m/%d/%Y")
                                        if j.end_date:
                                            end_date = time.strptime(
                                            j.end_date, "%m/%d/%Y")
                                        else:
                                            end_date = None
                                        send_at = time.strptime(
                                            j.send_at, "%I:%M %p")
                                        async with request.app['mysql'].acquire() as conn:
                                            async with conn.cursor(DictCursor) as cur:
                                                if j.id:
                                                    await cur.execute(
                                                        """
                                                        UPDATE surveys1
                                                        SET
                                                            title = %s,
                                                            category = %s,
                                                            department = %s,
                                                            start_date = %s,
                                                            end_date = %s,
                                                            send_at = TIME(%s),
                                                            weekly = %s,
                                                            question_order = %s,
                                                            `repeat` = %s
                                                        WHERE id = %s
                                                        """, (
                                                            j.title,
                                                            j.category,
                                                            j.department,
                                                            start_date,
                                                            end_date,
                                                            send_at,
                                                            j.weekly,
                                                            j.order,
                                                            j.repeat,
                                                            j.id
                                                        )
                                                    )
                                                else:
                                                    await cur.execute(
                                                    """
                                                    INSERT INTO surveys1
                                                    SET
                                                        title = %s,
                                                        category = %s,
                                                        department = %s,
                                                        start_date = %s,
                                                        end_date = %s,
                                                        send_at = TIME(%s),
                                                        weekly = %s,
                                                        question_order = %s,
                                                        `repeat` = %s
                                                    """,
                                                    (
                                                        j.title,
                                                        j.category,
                                                        j.department,
                                                        start_date,
                                                        end_date,
                                                        send_at,
                                                        j.weekly,
                                                        j.order,
                                                        j.repeat,
                                                    )
                                                )
                                                try:
                                                    await conn.commit()
                                                    log.debug(
                                                        f"Saved survey cron #{cur.lastrowid}")
                                                    if j.id:
                                                        await cur.execute(f"""
                                                            SELECT s.id, s.title, s.category, s.department, s.weekly, s.question_order, s.repeat, s.sent_count, s.receive_count, c.cat_name, c.cat_slug, DATE_FORMAT(start_date, '%m/%d/%Y') AS start_date, DATE_FORMAT(end_date, '%m/%d/%Y') AS end_date, TIME_FORMAT(send_at, '%h:%i %p') AS send_at, COUNT(q.id) AS question_count, DATEDIFF(NOW(), s.start_date) AS days_active
                                                            FROM surveys1 AS s
                                                            LEFT JOIN categories AS c
                                                            ON s.category=c.id
                                                            LEFT JOIN questions1 AS q
                                                            ON q.category = c.id
                                                            WHERE s.id = {j.id}""")
                                                    else:
                                                        await cur.execute(f"""
                                                            SELECT s.id, s.title, s.category, s.department, s.weekly, s.question_order, s.repeat, s.sent_count, s.receive_count, c.cat_name, c.cat_slug, DATE_FORMAT(start_date, '%m/%d/%Y') AS start_date, DATE_FORMAT(end_date, '%m/%d/%Y') AS end_date, TIME_FORMAT(send_at, '%h:%i %p') AS send_at, COUNT(q.id) AS question_count, DATEDIFF(NOW(), s.start_date) AS days_active
                                                            FROM surveys1 AS s
                                                            LEFT JOIN categories AS c
                                                            ON s.category=c.id
                                                            LEFT JOIN questions1 AS q
                                                            ON q.category = c.id
                                                            WHERE s.id = {cur.lastrowid}""")
                                                    survey = await cur.fetchone()
                                                    await wsr.reply({
                                                        'success': True,
                                                        'msg': 'Scheduled survey',
                                                        'survey': survey
                                                    })
                                                except Exception as ex:
                                                    log.exception(ex)
                                                continue
                                    else:
                                        await ws.send_json({
                                            'success': False,
                                            'data': j,
                                            "puid": j.puid if 'puid' in j else "00"
                                        })
                                        continue
                                except web.HTTPUnauthorized as ex:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': str(ex)
                                    })
                                    continue

                            if case('add_schedule_lite'):
                                try:
                                    _auth = await init_auth(request, protect=True, permission='user')
                                    if _auth.logged_in:
                                        # TODO: Proper validators
                                        if 'cron_schedule' not in j or len(j.cron_schedule) < 1 or j.cron_schedule == '0':
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'No recurring schedule specified.'
                                            })
                                            continue
                                        # FIXME: Parse our quartz cron
                                        """try:
                                            tzcron.Schedule(j.msg.cron_schedule, pytz.utc)
                                            if CronValidator.parse(j.msg.cron_schedule) is None:
                                                await wsr.reply({
                                                    'success': False,
                                                    'msg': 'Invalid cron string specified.'
                                                })
                                                continue
                                        except ValueError:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Invalid cron string caused value error.',
                                                'cron_string': j.msg.cron_schedule
                                            })
                                            continue"""
                                        if 'use_random' not in j or (j.use_random != 'True' and j.use_random != 'False'):
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Use random not specified.'
                                            })
                                            continue
                                        if 'depts' not in j or len(j.depts) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'No departments specified'
                                            })
                                            continue
                                        surveys_cat_questions = False
                                        if 'surveys' in j and len(j.surveys) > 0:
                                            surveys_cat_questions = True
                                        if 'questions' in j and len(j.questions) > 0:
                                            surveys_cat_questions = True
                                            try:
                                                j.questions = to_data(
                                                    ujson.loads(j.questions))
                                            except JSONDecodeError:
                                                wsr.reply({
                                                    'success': False,
                                                    'msg': 'Unable to parse questions.'
                                                })
                                                continue
                                        if 'cat' in j:
                                            try:
                                                j.cat = int(j.cat)
                                                surveys_cat_questions = True
                                            except ValueError:
                                                await wsr.reply({
                                                    'success': False,
                                                    'msg': 'Invalid category specified.'
                                                })
                                                continue
                                        if not surveys_cat_questions:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Must specify a category, survey(s) or question(s).'
                                            })
                                            continue
                                        if 'title' not in j or len(j.title) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'title not speficied.'
                                            })
                                            continue
                                        if 'start_date' not in j or len(j.start_date) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Start date not speficied.'
                                            })
                                            continue
                                        if 'end_date' not in j or len(j.start_date) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'End date not speficied.'
                                            })
                                            continue
                                        if 'tags' not in j or len(j.tags) < 1:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Tags not speficied.'
                                            })
                                            continue
                                        """if 'cat' not in j or not isinstance(j.cat, int):
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Category not speficied.'
                                            })
                                            continue"""
                                        cron_descr = ExpressionDescriptor(
                                            expression=j.cron_schedule,
                                            throw_exception_on_parse_error=True,
                                            casing_type=CasingTypeEnum.Sentence,
                                            use_24hour_time_format=False
                                        )
                                        start_date = time.strptime(
                                            j.start_date, "%b %d,%Y %I:%M %p")
                                        end_date = time.strptime(
                                            j.end_date, "%b %d,%Y %I:%M %p")
                                        tags = [t.value for t in j.tags]
                                        async with request.app['mysql'].acquire() as conn:
                                            async with conn.cursor(DictCursor) as cur:
                                                await cur.execute(
                                                    """
                                                    INSERT INTO crons
                                                    SET
                                                        user_id = %s,
                                                        cron = %s,
                                                        use_random = %s,
                                                        start_date = %s,
                                                        end_date = %s,
                                                        title = %s,
                                                        depts = %s,
                                                        surveys = %s,
                                                        tags = %s,
                                                        cat = %s,
                                                        questions = %s
                                                    """, (_auth.user_id,
                                                          j.cron_schedule,
                                                          1 if j.use_random else 0,
                                                          start_date,
                                                          end_date,
                                                          j.title,
                                                          mo_dumps(j.depts),
                                                          mo_dumps(j.surveys),
                                                          mo_dumps(tags),
                                                          mo_dumps(j.cat),
                                                          mo_dumps(j.questions),))
                                                try:
                                                    s = 's' if len(
                                                        j.surveys) > 0 else ''
                                                    scheduled_msg = f'Survey{s} scheduled {fmt_cron(cron_descr.get_description())}'
                                                    await conn.commit()
                                                    log.debug(
                                                        f"Saved survey cron #{cur.lastrowid}")
                                                except Exception as ex:
                                                    log.exception(ex)
                                                await wsr.reply({
                                                    'success': True,
                                                    'msg': scheduled_msg,
                                                })
                                                continue
                                    else:
                                        await ws.send_json({
                                            'success': False,
                                            'data': j,
                                            "puid": j.puid if 'puid' in j else "00"
                                        })
                                        continue
                                except web.HTTPUnauthorized as ex:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': str(ex)
                                    })
                                    continue

                            if case('send_invites'):
                                try:
                                    _auth = await init_auth(request, protect=True, permission='user')
                                    if _auth.logged_in:

                                        if 'invite_emails' not in j and 'mobile_numbers' not in j:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'No email addresses or phone numbers specified.'
                                            })
                                            continue
                                        if 'dept' not in j or ('dept' in j and j.dept in ('0', 0, '')):
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'You must choose a department.'
                                            })
                                            continue

                                        org_depts = to_data(await depts_of_org(auth.org, request.app['mysql']))
                                        dept_exists = False
                                        for _dept in org_depts:
                                            if j.dept == _dept.id:
                                                dept_exists = True
                                                this_dept = _dept
                                        if not dept_exists:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'Invalid department given.'
                                            })
                                            continue
                                        async with request.app['mysql'].acquire() as conn:
                                            async with conn.cursor(DictCursor) as cur:

                                                # Nested function to gen codes
                                                async def unique_invite():
                                                    _invite_code = pwd.genword(
                                                        length=6, charset="ascii_62")
                                                    await cur.execute(
                                                        """
                                                        SELECT `id`
                                                        FROM users
                                                        WHERE invite_code = %s
                                                        LIMIT 1""",
                                                        (_invite_code,))
                                                    return _invite_code if await cur.fetchone() is None else False

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
                                                sql_values = (_auth['user_id'],
                                                              1 if this_dept.slug == "management" else 0,
                                                              _auth['org'],
                                                              this_dept.slug,
                                                              _auth['company_name'],)
                                                crypt_context = CryptContext(
                                                    schemes=["argon2"])
                                                invite_cnt = 0
                                                # TODO: validate emails
                                                if 'invite_emails' in j and len(j.invite_emails) > 0:
                                                    # to_data(ujson.loads(j.invite_emails))
                                                    invite_emails = j.invite_emails
                                                    for email in invite_emails:
                                                        await cur.execute(
                                                            """SELECT *
                                                            FROM users
                                                            WHERE
                                                                email_address = %s
                                                            """, (email,))
                                                        inv_exists = await cur.fetchone()
                                                        this_uid = inv_exists['id'] if inv_exists is not None else None
                                                        if inv_exists is None or len(inv_exists) == 0:

                                                            temp_pass = pwd.genword(
                                                                length=15, charset="ascii_72")
                                                            while True:  # FIXME: Refactor this loop into its def
                                                                if invite_code := await unique_invite():
                                                                    break
                                                            hashed_pass = crypt_context.hash(
                                                                temp_pass)
                                                            await cur.execute(f'{sql_query}, email_address = %s',
                                                                              sql_values + (hashed_pass,
                                                                                            invite_code.replace(
                                                                                                ' ', ''),
                                                                                            email,))
                                                            await conn.commit()
                                                            this_uid = cur.lastrowid
                                                            login = f"user{this_uid}"
                                                            await cur.execute("UPDATE users SET login = %s WHERE id = %s",
                                                                              (login, this_uid,))
                                                        await cur.execute(
                                                            """
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
                                                                  f"Your employer has invited you to Hiyer. Sign up {ENV.URL_PROTO}{ENV.SITE_DOMAIN}/i/{invite_code}",))
                                                        await conn.commit()
                                                        invite_cnt += 1

                                                if 'mobile_numbers' in j and len(j.mobile_numbers) > 0:
                                                    # to_data(ujson.loads(j.mobile_numbers))
                                                    invite_numbers = j.mobile_numbers
                                                    for num in invite_numbers:
                                                        await cur.execute(
                                                            """SELECT *
                                                            FROM users
                                                            WHERE
                                                                mobile_number = %s
                                                            """, (num,))
                                                        inv_exists = await cur.fetchone()
                                                        this_uid = inv_exists['id'] if inv_exists is not None else None
                                                        if inv_exists is None or len(inv_exists) == 0:
                                                            temp_pass = pwd.genword(
                                                                length=15, charset="ascii_72")
                                                            while True:
                                                                if invite_code := await unique_invite():
                                                                    break
                                                            hashed_pass = crypt_context.hash(
                                                                temp_pass)
                                                            await cur.execute(f'{sql_query}, mobile_number = %s',
                                                                              sql_values + (hashed_pass,
                                                                                            invite_code.replace(
                                                                                                ' ', ''),
                                                                                            f"+{strip_nonnumeric(num)}",))
                                                            await conn.commit()
                                                            this_uid = cur.lastrowid
                                                            login = f"user{this_uid}"
                                                            await cur.execute("UPDATE users SET login = %s WHERE id = %s",
                                                                              (login, this_uid,))
                                                        await cur.execute(
                                                            """
                                                            INSERT INTO notifications
                                                            SET
                                                                user_id = %s,
                                                                calling_path = 'invite_user',
                                                                title = 'Hiyer Invite',
                                                                msg = %s,
                                                                icon = 'flat-color-icons:invite'
                                                                """, (this_uid,
                                                                      f"Your employer has invited you to Hiyer. Sign up {ENV.URL_PROTO}{ENV.SITE_DOMAIN}/i/{invite_code}",))
                                                        await conn.commit()
                                                        invite_cnt += 1
                                                await wsr.reply({
                                                    'success': not not invite_cnt,
                                                    'msg': f'Invited {invite_cnt} employees.' if invite_cnt else 'No valid emails or phone numbers given.'
                                                })
                                                continue
                                    else:
                                        await wsr.reply({
                                            'success': False,
                                            'msg': "You're not logged in."
                                        })
                                        continue
                                except json.JSONDecodeError as ex:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': 'Invalid invite input.'
                                    })
                                    continue
                                except web.HTTPUnauthorized as ex:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': str(ex)
                                    })
                                    continue

                            if case('update_settings'):
                                _auth = await init_auth(request, protect=True, permission='user')
                                if _auth.logged_in:
                                    add_sql = ""
                                    add_val = ()
                                    if 'current_password' not in j.data:
                                        await wsr.reply({
                                            'success': False,
                                            'msg': 'Current password not specified.'
                                        })
                                        continue
                                    if 'mobile_number' not in j.data:
                                        await wsr.reply({
                                            'success': False,
                                            'msg': 'No mobile number specified.'
                                        })
                                        continue
                                    if 'password' in j.data:
                                        if 'password_repeat' not in j.data:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': 'No password repeat specified.'
                                            })
                                            continue
                                        if j.data.password != j.data.password_repeat:
                                            await wsr.reply({
                                                'success': False,
                                                'msg': "Passwords don't match."
                                            })
                                            continue
                                        password_hash = request.app['argon2'].hash(
                                            j.data.password)
                                        add_sql += ", password_hash = %s"
                                        add_val += (password_hash,)
                                    async with request.app['mysql'].acquire() as conn:
                                        async with conn.cursor(DictCursor) as cur:
                                            await cur.execute(f"""
                                            SELECT password_hash FROM users
                                            WHERE
                                                id = %s
                                            """, (_auth.user_id,))
                                            if user_match := await cur.fetchone():
                                                if not request.app['argon2'].verify(j.data.current_password, user_match['password_hash']):
                                                    await wsr.reply({
                                                        'success': False,
                                                        'msg': "The current password supplied is incorrect."
                                                    })
                                                    continue
                                            else:
                                                await wsr.reply({
                                                    'success': False,
                                                    'msg': "Error locating user account."
                                                })
                                                continue

                                            async with conn.cursor(DictCursor) as cur:
                                                await cur.execute(f"""
                                                UPDATE users
                                                SET
                                                    mobile_number = %s,
                                                    email_address = %s
                                                    {add_sql}
                                                WHERE
                                                    id = %s
                                                """, (j.data.mobile_number,
                                                      j.data.email_address,
                                                      _auth.user_id,)+add_val)
                                                await wsr.reply({
                                                    'success': True,
                                                    'msg': 'Settings saved.'
                                                })
                                                continue

                            if case('do_register'):
                                _auth = await init_auth(request, protect=False)
                                if _auth.logged_in:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': 'You already have an account.'
                                    })
                                    continue
                                request['ws_post'] = j
                                request['ws_post'].get = lambda x: request['ws_post'][x]
                                reg_success, msg = await do_register(request)
                                await wsr.reply({
                                    'success': reg_success,
                                    'msg': msg
                                })
                                continue

                            if case('survey_list'):
                                async with request.app['mysql'].acquire() as conn:
                                    async with conn.cursor(DictCursor) as cur:
                                        await cur.execute("""SELECT s.*, c.cat_name, c.cat_slug
                                            FROM surveys1 AS s
                                            LEFT JOIN categories AS c
                                            ON s.category=c.id""")
                                        surveys = await cur.fetchall()
                                        await wsr.reply({
                                            'surveys': surveys
                                        })
                                continue
                            
                            if case('answer'):
                                if 'invite_id' not in j or 'answer' not in j:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': 'Wrong operation'
                                    })
                                    continue
                                async with request.app['mysql'].acquire() as conn:
                                    async with conn.cursor(DictCursor) as cur:
                                        await cur.execute("""
                                            UPDATE survey_invites1 SET answer = %s, answered_at = NOW()
                                            WHERE id = %s AND NOT answer
                                        """, (j.answer, j.invite_id))
                                        await conn.commit()

                                    if cur.rowcount:
                                        await wsr.reply({
                                            'success': True,
                                            'msg': 'Success'
                                        })
                                    else:
                                        await wsr.reply({
                                            'success': False,
                                            'msg': 'Already answered'
                                        })
                                continue

                            if case('trash_survey'):
                                if 'id' not in j:
                                    await wsr.reply({
                                        'success': False,
                                        'msg': 'Select one survey'
                                    })
                                async with request.app['mysql'].acquire() as conn:
                                    async with conn.cursor(DictCursor) as cur:
                                        await cur.execute("""
                                            DELETE FROM surveys1 WHERE id = %s;
                                            DELETE FROM survey_invites1 WHERE survey_id = %s;
                                        """, (j.id, j.id))
                                        await conn.commit()

                                await wsr.reply({
                                    'success': True,
                                    'msg': 'Success',
                                    'id': j.id
                                })
                                continue

                            if case('score_data'):
                                date_range_where = ''
                                if j.date_range == 'custom':
                                    date_range_where = f"""AND Date(i.answered_at) >= DATE('{j.start_date}') AND Date(i.answered_at) <= DATE('{j.end_date}')"""
                                    before_where = f"""Date(i.answered_at) < DATE('{j.start_date}')"""
                                elif j.date_range == '7d':
                                    date_range_where = 'AND Date(i.answered_at) >= DATE_SUB(DATE(NOW()), INTERVAL 7 DAY)'
                                    before_where = f"""Date(i.answered_at) < DATE_SUB(DATE(NOW()), INTERVAL 7 DAY)"""
                                elif j.date_range == '1m':
                                    date_range_where = 'AND Date(i.answered_at) >= DATE_SUB(DATE(NOW()), INTERVAL 1 MONTH)'
                                    before_where = f"""Date(i.answered_at) < DATE_SUB(DATE(NOW()), INTERVAL 1 MONTH)"""
                                elif j.date_range == '3m':
                                    date_range_where = 'AND Date(i.answered_at) >= DATE_SUB(DATE(NOW()), INTERVAL 3 MONTH)'
                                    before_where = f"""Date(i.answered_at) < DATE_SUB(DATE(NOW()), INTERVAL 3 MONTH)"""
                                elif j.date_range == '1Y':
                                    date_range_where = 'AND Date(i.answered_at) >= DATE_SUB(DATE(NOW()), INTERVAL 1 YEAR)'
                                    before_where = f"""Date(i.answered_at) < DATE_SUB(DATE(NOW()), INTERVAL 1 YEAR)"""

                                min_scores = {}
                                async with request.app['mysql'].acquire() as conn:
                                    async with conn.cursor(DictCursor) as cur:
                                        await cur.execute(f"""
                                            SELECT c.cat_name, c.cat_slug, SUM(i.answer) AS total, COUNT(i.answer) AS cnt, DATE_FORMAT(i.answered_at, '%Y-%c-%e') AS date_info
                                            FROM survey_invites1 AS i
                                            LEFT JOIN surveys1 AS s
                                            ON i.survey_id = s.id
                                            LEFT JOIN categories AS c
                                            ON s.category = c.id
                                            WHERE NOT ISNULL(i.answer) AND NOT ISNULL(s.id)
                                            {date_range_where}
                                            GROUP BY c.id, date_info
                                        """)
                                        data  = await cur.fetchall()
                                        
                                        for i in range(1, 4):
                                            await cur.execute(f"""
                                                SELECT c.cat_slug, SUM(i.answer) AS total, COUNT(i.answer) AS cnt, DATE_FORMAT(i.answered_at, '%Y-%c-%e') AS date_info
                                                FROM survey_invites1 AS i
                                                LEFT JOIN surveys1 AS s
                                                ON i.survey_id = s.id
                                                LEFT JOIN categories AS c
                                                ON s.category = c.id
                                                WHERE NOT ISNULL(i.answer) AND NOT ISNULL(s.id) AND s.category = {i}
                                                GROUP BY c.id, date_info
                                                ORDER BY date_info DESC
                                            """)
                                            row = await cur.fetchone()

                                            if row:
                                                min_scores[row['cat_slug']] = row

                                result = {}
                                for row in data:
                                    result[row['date_info'] + row['cat_slug']] = row

                                await wsr.reply({
                                    'success': True,
                                    'result': result,
                                    'min_scores': min_scores
                                })
                                continue
                            
                            if case('save-dept'):
                                async with request.app['mysql'].acquire() as conn:
                                    async with conn.cursor(DictCursor) as cur:
                                        if j.id:
                                            await cur.execute("""
                                                UPDATE departments SET dept_name = %s WHERE id = %s
                                            """, (j.name, j.id))
                                        else:
                                            await cur.execute("""
                                                INSERT INTO departments SET dept_name = %s, org = %s
                                            """, (j.name, j.org))
                                        await conn.commit()

                                        if j.id:
                                            await cur.execute(f"""
                                                SELECT * FROM departments WHERE id = {j.id}
                                            """)
                                        else:
                                            await cur.execute(f"""
                                                SELECT * FROM departments WHERE id = {cur.lastrowid}
                                            """)
                                        data  = await cur.fetchone()

                                await wsr.reply({
                                    'success': True,
                                    'msg': 'Success',
                                    'department': data
                                })
                                continue
                            
                            if case('delete-dept'):
                                async with request.app['mysql'].acquire() as conn:
                                    async with conn.cursor(DictCursor) as cur:
                                        await cur.execute(f"""
                                            DELETE FROM departments WHERE id = {j.id}
                                        """)
                                        await conn.commit()

                                await wsr.reply({
                                    'success': True,
                                    'msg': 'Success',
                                    'id': j.id
                                })
                                continue

                            if case('copy_survey'):
                                async with request.app['mysql'].acquire() as conn:
                                    async with conn.cursor(DictCursor) as cur:
                                        await cur.execute(f"""
                                            INSERT INTO surveys1 (title, category, department, start_date, end_date, weekly, send_at, question_order, `repeat`)
                                            SELECT title, category, department, start_date, end_date, weekly, send_at, question_order, `repeat`
                                            FROM surveys1
                                            WHERE id = {j.id}
                                        """)
                                        await conn.commit()
                                    
                                        await cur.execute(f"""
                                            SELECT s.id, s.title, s.category, s.department, s.weekly, s.question_order, s.repeat, s.sent_count, s.receive_count, c.cat_name, c.cat_slug, DATE_FORMAT(start_date, '%m/%d/%Y') AS start_date, DATE_FORMAT(end_date, '%m/%d/%Y') AS end_date, TIME_FORMAT(send_at, '%h:%i %p') AS send_at, COUNT(q.id) AS question_count, DATEDIFF(NOW(), s.start_date) AS days_active
                                            FROM surveys1 AS s
                                            LEFT JOIN categories AS c
                                            ON s.category=c.id
                                            LEFT JOIN questions1 AS q
                                            ON q.category = c.id
                                            WHERE s.id = {cur.lastrowid}
                                        """)
                                        survey  = await cur.fetchone()

                                await wsr.reply({
                                    'success': True,
                                    'msg': 'Success',
                                    'survey': survey
                                })
                                continue

                            if case.default:
                                await wsr.reply({
                                    'success': False,
                                    'data': j,
                                    'msg': 'Invalid API endpoint.'
                                })

                except ValueError as ex:
                    await wsr.reply({
                        'success': False,
                        'msg': ex
                    })
                    continue
                # request.app['skip_disconnect'] = True  # FIXME: Reassignment not working here.
                if data == 'close':
                    await ws.close()
            elif msg.type == aiohttp.MsgType.closed:
                await close_ws_atomic(request, ws)
                break
                raise ConnectionAbortedError(msg.type)
            elif msg.type == aiohttp.MsgType.error:
                await close_ws_atomic(request, ws)
                break
                raise ConnectionError(msg.type)
            elif msg.type == WSMsgType.ERROR:
                await close_ws_atomic(request, ws)
                break
                raise ConnectionError(msg.type)
    except ConnectionError as ex:
        await close_ws_atomic(request, ws)
    except Exception as ex:
        log.warning("Unhandled exception encountered in WS route.")
        log.exception(ex)
    finally:
        """if not request.app['skip_disconnect']:
            request.app["websockets"].remove(ws)
        else:
            skip_disconnect = True"""
        pass

    log.debug('websocket connection closed')
    return ws
