import csv
import tempfile
import aiohttp_csrf
import aiohttp_jinja2
from aiohttp import web
import ujson
from aiomysql import DictCursor
from mo_dots import to_data
from questions import Form, RadioGroupQuestion, RatingQuestion

from auth import init_auth
from common import ENV, departments, mo_dumps, safe_dumps


class HiyerRatingForm(Form):
    question = RatingQuestion(rate_min=1, rate_max=10,
                              rate_step=1, title="Question 1", required=True)


# section user_home
@aiohttp_jinja2.template('dashboard.html')
@aiohttp_csrf.csrf_exempt
async def dashboard(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {
        'page_title': "Your Dashboard",
        'csrf': csrf_token,
        'auth': auth,
        'ENV': ENV,
        'colors': request.app['colors'],
        'this_page': request.rel_url,
    }


@aiohttp_jinja2.template('create_simple.html')
async def create_simple(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    csrf_token = await aiohttp_csrf.generate_token(request)
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                """
                SELECT * FROM questions
                WHERE
                    user_id = %s
                """, (auth['user_id'],))
            questions = await cur.fetchall()
            if questions is not None:
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
                    'tags': [t for t in [_q.tag1, _q.tag2, _q.tag3] if t is not None]
                } for _q in to_data(questions)]
            questions = ujson.loads(safe_dumps(questions))

    return {
        'page_title': "Create Surveys",
        'csrf': csrf_token,
        'auth': auth,
        'ENV': ENV,
        'colors': request.app['colors'],
        'questions': questions
    }


# section orgs
@aiohttp_jinja2.template('orgs.html')
@aiohttp_csrf.csrf_exempt
async def orgs(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)

    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                """
                SELECT * FROM orgs
                WHERE
                    user_id = %s
                """, (auth['user_id'],))
            org = await cur.fetchone()

            await cur.execute("""
                SELECT * FROM departments WHERE org = %s
                """, org['id'])
            departments = await cur.fetchall()
            
            await cur.execute("""
                SELECT u.id, u.first_name, u.last_name, u.email_address, u.dept, d.dept_name, IFNULL(COUNT(i.answer) / COUNT(i.id) * 100, 0) AS response_rate,
                IFNULL(SUM(i.answer) / COUNT(i.answer) * 10, 0) AS peer_review
                FROM users AS u
                LEFT JOIN survey_invites1 AS i
                ON i.user_id = u.id
                LEFT JOIN departments AS d
                ON u.dept = d.id
                WHERE u.org = %s AND NOT u.is_employer AND NOT is_new_user
                GROUP BY u.id
            """, org['id'])
            employees = await cur.fetchall()
            
            await cur.execute("""SELECT * FROM categories""")
            categories = await cur.fetchall()

    return {
        'page_title': "Your Organization",
        'csrf': csrf_token,
        'auth': auth,
        'ENV': ENV,
        'org': org,
        'departments': departments,
        'employees': employees,
        'categories': categories,
        'colors': request.app['colors']
    }


# section user_settings
@aiohttp_jinja2.template('user_settings.html')
@aiohttp_csrf.csrf_exempt
async def user_settings(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {'page_title': "Your Settings", 'csrf': csrf_token, 'auth': auth, 'ENV': ENV}


# section user_settings
@aiohttp_jinja2.template('calendar.html')
@aiohttp_csrf.csrf_exempt
async def calendar(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {'page_title': "Your Calendar", 'csrf': csrf_token, 'auth': auth, 'ENV': ENV}


# section user_stats
@aiohttp_jinja2.template('stats.html')
@aiohttp_csrf.csrf_exempt
async def user_stats(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("""
                SELECT SUM(s.sent_count) AS sent_count, SUM(s.receive_count) AS receive_count
                FROM categories AS c
                LEFT JOIN surveys1 AS s
                ON c.id = s.category
            """)
            rate = await cur.fetchone()

            await cur.execute("""
                SELECT c.cat_name, c.cat_slug, SUM(i.answer) AS total, COUNT(i.answer) AS cnt
                FROM survey_invites1 AS i
                LEFT JOIN surveys1 AS s
                ON i.survey_id = s.id
                LEFT JOIN categories c
                ON s.category = c.id
                WHERE NOT ISNULL(i.answer) AND NOT ISNULL(s.id)
                GROUP BY c.id
            """)
            categories  = await cur.fetchall()

            await cur.execute("""
                SELECT COUNT(*) AS question_count FROM questions1
            """)
            data = await cur.fetchone()
            question_count = data['question_count']

            await cur.execute("""
                SELECT COUNT(*) AS employee_count FROM users WHERE NOT is_employer AND NOT is_new_user
            """)
            data = await cur.fetchone()
            employee_count = data['employee_count']

            await cur.execute("""
                SELECT d.id, d.dept_name, IFNULL(SUM(s.receive_count) / SUM(s.sent_count) * 100, 0) AS response_rate, IFNULL(SUM(i.answer) / COUNT(i.answer) * 10, 0) AS peer_review
                FROM departments AS d
                LEFT JOIN surveys1 AS s
                ON d.id = s.department
                LEFT JOIN survey_invites1 AS i
                ON s.id = i.survey_id
                WHERE d.org = %s
                GROUP BY d.id
                LIMIT 5
            """, auth['org'])
            department_rates = await cur.fetchall()

            await cur.execute("""
                SELECT u.id, u.first_name, u.last_name, IFNULL(COUNT(i.answer) / COUNT(i.id) * 100, 0) AS response_rate, IFNULL(SUM(i.answer) / COUNT(i.answer) * 10, 0) AS peer_review
                FROM users AS u
                LEFT JOIN survey_invites1 AS i
                ON i.user_id = u.id
                WHERE u.org = %s AND NOT is_new_user
                GROUP BY u.id
                LIMIT 5
            """, auth['org'])
            employee_rates = await cur.fetchall()

            response_rate = {
                'total': 0
            }
            for category in categories:
                percent = int(category['total'] / category['cnt'] * 10)
                response_rate[category['cat_slug']] = percent
            
            if rate and rate['receive_count']:
                response_rate['total'] = int(rate['receive_count'] / rate['sent_count'] * 100)

    return {
        'page_title': "Your Stats",
        'csrf': csrf_token,
        'auth': auth,
        'ENV': ENV,
        'response_rate': response_rate,
        'question_count': question_count,
        'employee_count': employee_count,
        'department_rates': department_rates,
        'employee_rates': employee_rates,
        'this_page': request.rel_url,
        'cat_colors': {
            'performance': '#FF5B61',
            'peer-review': '#636F9A',
            'managed-up': '#29E7CD',
            'cqi': '#FF5BC3',
        },
    }


# section survey_stats
@aiohttp_jinja2.template('survey_stats.html')
@aiohttp_csrf.csrf_exempt
async def survey_stats(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    survey_id = request.match_info['survey_id'] if 'survey_id' in request.match_info else None
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(f"""
                SELECT s.id, s.title, s.category, s.department, s.weekly, s.question_order, s.sent_count, s.receive_count, COUNT(q.id) AS question_count, DATEDIFF(NOW(), s.start_date) AS days_active
                FROM surveys1 AS s
                LEFT JOIN categories AS c
                ON s.category=c.id
                LEFT JOIN questions1 AS q
                ON q.category = c.id
                WHERE s.id = {survey_id}
                GROUP BY s.id 
            """)
            stats_data = await cur.fetchone()

            await cur.execute(f"""
                SELECT IFNULL(SUM(i.answer) / COUNT(i.id), 0) AS average
                FROM surveys1 AS s
                LEFT JOIN survey_invites1 i
                ON s.id = i.survey_id
                WHERE s.id = {survey_id} AND NOT ISNULL(i.answer)
            """)
            data = await cur.fetchone()
            stats_data['average'] = data['average']

            await cur.execute(f"""
                SELECT q.id, q.question, i.answer, COUNT(i.answer) AS a_cnt
                FROM survey_invites1 AS i
                LEFT JOIN questions1 AS q
                ON q.id = i.question_id
                WHERE i.survey_id = {survey_id} AND NOT ISNULL(i.answer)
                GROUP BY q.id, i.answer
            """)
            data = await cur.fetchall()
            chart_data = {}
            for row in data:
                if row['id'] not in chart_data:
                    chart_data[row['id']] = {}
                    chart_data[row['id']]['question'] = row['question']
                    chart_data[row['id']]['data'] = {}
                chart_data[row['id']]['data'][row['answer']] = row['a_cnt']

            # await cur.execute(f"""
            #     SELECT q.id, q.question, i.answer
            #     FROM survey_invites1 AS i
            #     LEFT JOIN questions1 AS q
            #     ON q.id = i.question_id
            #     WHERE i.survey_id = {survey_id} AND NOT ISNULL(i.answer)
            #     ORDER BY i.question_id
            # """)
            # data = await cur.fetchall()
            # chart_data = {}
            # for row in data:
            #     if row['id'] not in chart_data:
            #         chart_data[row['id']] = {}
            #         chart_data[row['id']]['question'] = row['question']
            #         chart_data[row['id']]['data'] = []
            #     chart_data[row['id']]['data'].append(row['answer'])


    return {
        'page_title': "Survey Stats",
        'csrf': csrf_token,
        'auth': auth,
        'ENV': ENV,
        'stats_data': stats_data,
        'chart_data': chart_data,
    }


# section question_stats
@aiohttp_jinja2.template('question_stats.html')
@aiohttp_csrf.csrf_exempt
async def question_stats(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    question_id = request.match_info['question_id'] if 'question_id' in request.match_info else None
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(f"""
                SELECT q.question, COUNT(i.id) AS sent_count, COUNT(i.answer) AS receive_count, IFNULL(SUM(i.answer) / COUNT(i.id), 0) AS average, COUNT(DISTINCT i.survey_id) AS survey_count
                FROM questions1 q
                LEFT JOIN survey_invites1 i
                ON q.id = i.question_id
                WHERE q.id = {question_id}
            """)
            stats_data = await cur.fetchone()

    return {
        'page_title': "Survey Stats",
        'csrf': csrf_token,
        'auth': auth,
        'ENV': ENV,
        'stats_data': stats_data
    }


# section category_stats
@aiohttp_jinja2.template('category_stats.html')
@aiohttp_csrf.csrf_exempt
async def category_stats(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    category_id = request.match_info['category_id'] if 'category_id' in request.match_info else None
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(f"""
                SELECT c.id, c.cat_name, SUM(s.sent_count) AS sent_count, SUM(s.receive_count) receive_count, COUNT(DISTINCT q.id) AS question_count
                FROM categories AS c
                LEFT JOIN surveys1 AS s
                ON s.category=c.id
                LEFT JOIN questions1 AS q
                ON q.category = c.id
                WHERE c.id = {category_id}
                GROUP BY c.id
            """)
            stats_data = await cur.fetchone()

            await cur.execute(f"""
                SELECT IFNULL(SUM(i.answer) / COUNT(i.id), 0) AS average
                FROM surveys1 AS s
                LEFT JOIN survey_invites1 i
                ON s.id = i.survey_id
                WHERE s.category = {category_id} AND NOT ISNULL(i.answer)
            """)
            data = await cur.fetchone()
            stats_data['average'] = data['average']

            await cur.execute(f"""
                SELECT q.id, q.question, i.answer, COUNT(i.answer) AS a_cnt
                FROM survey_invites1 AS i
                LEFT JOIN questions1 AS q
                ON q.id = i.question_id
                WHERE q.category = {category_id} AND NOT ISNULL(i.answer)
                GROUP BY q.id, i.answer
            """)
            data = await cur.fetchall()
            chart_data = {}
            for row in data:
                if row['id'] not in chart_data:
                    chart_data[row['id']] = {}
                    chart_data[row['id']]['question'] = row['question']
                    chart_data[row['id']]['data'] = {}
                chart_data[row['id']]['data'][row['answer']] = row['a_cnt']

    return {
        'page_title': "Survey Stats",
        'csrf': csrf_token,
        'auth': auth,
        'ENV': ENV,
        'stats_data': stats_data,
        'chart_data': chart_data
    }


# section answer
@aiohttp_jinja2.template('answer.html')
@aiohttp_csrf.csrf_exempt
async def answer(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='employee')
    csrf_token = await aiohttp_csrf.generate_token(request)
    qid = request.match_info['qid'] if 'qid' in request.match_info else None
    return {'page_title': "Answer Questions",
            'csrf': csrf_token,
            'auth': auth,
            'msg': '',
            'ENV': ENV,
            'qid': qid}


# section show survey and answer
@aiohttp_jinja2.template('survey.html')
@aiohttp_csrf.csrf_exempt
async def survey(request):
    auth = await init_auth(request, protect=True, permission='employee')
    if auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    survey_invite_id = request.match_info['survey_invite_id'] if 'survey_invite_id' in request.match_info else None
    
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            if survey_invite_id:
                # TODO: set notification seen value
                await cur.execute("""
                    SELECT i.*, s.title, q.question, q.type
                    FROM survey_invites1 AS i
                    LEFT JOIN surveys1 AS s ON i.survey_id = s.id
                    LEFT JOIN questions1 AS q ON i.question_id = q.id
                    WHERE user_id = %s AND i.id = %s AND NOT ISNULL(s.id)
                """, (auth.user_id, survey_invite_id))
            else:
                # TODO: set notification seen value
                await cur.execute("""
                    SELECT i.*, s.title, q.question, q.type
                    FROM survey_invites1 AS i
                    LEFT JOIN surveys1 AS s ON i.survey_id = s.id
                    LEFT JOIN questions1 AS q ON i.question_id = q.id
                    WHERE user_id = %s AND ISNULL(i.answer) AND NOT ISNULL(s.id)
                """, (auth.user_id))

            questions = await cur.fetchall()

    return {
        'page_title': "Take Survey",
        'csrf': csrf_token,
        'auth': auth,
        'msg': '',
        'ENV': ENV,
        'questions': questions,
    }


# async def survey(request):
#     # session = await init_session(request)
#     auth = await init_auth(request, protect=True, permission='employee')
#     csrf_token = await aiohttp_csrf.generate_token(request)
#     survey_uuid = request.match_info['survey_uuid'] if 'survey_uuid' in request.match_info else None
#     question_id = int(request.match_info['qid']) if 'qid' in request.match_info and request.match_info['qid'] not in (
#         None, '', '0') else None
#     _survey, _question = None, None
#     async with request.app['mysql'].acquire() as conn:
#         async with conn.cursor(DictCursor) as cur:
#             if survey_uuid is not None:
#                 await cur.execute(
#                     """SELECT *
#                     FROM surveys
#                     WHERE survey_uuid = %s
#                     LIMIT 1
#                     """, (survey_uuid,))
#                 _survey = await cur.fetchone()
#                 if _survey is not None:
#                     _survey = to_data(_survey) if _survey is not None else None
#                     if 'survey_json' in _survey:
#                         _survey.json = to_data(
#                             ujson.loads(_survey.survey_json))
#                     if question_id is not None:
#                         await cur.execute(
#                             """
#                             SELECT sq.id as id,
#                             s.survey_uuid,
#                             s.survey_json,
#                             sq.org as org,
#                             sq.question as question_json,
#                             sq.cat as cat,
#                             s.survey_title as survey_title,
#                             s.id as survey_id
#                             FROM survey_questions sq
#                             JOIN surveys s
#                             ON sq.survey_id = s.id
#                             AND s.id = %s
#                             AND sq.qid = %s
#                             """, (_survey.id, question_id,))
#                         _question = await cur.fetchone()
#                         if _question is not None:
#                             _question = to_data(_question)
#                             if 'question_json' in _question:
#                                 _question.json = to_data(
#                                     ujson.loads(_question.question_json))
#                                 if _question.json.type == 'rating':
#                                     _question.rateMin = 1
#                                     _question.rateMax = 10
#                                     _question.json.rateMin = 1
#                                     _question.json.rateMax = 10
#     return {'page_title': "Take Survey",
#             'csrf': csrf_token,
#             'auth': auth,
#             'msg': '',
#             'ENV': ENV,
#             'survey_id': survey_uuid,
#             'survey': _survey,
#             'question_id': question_id,
#             'question': _question,
#             'no_bread': True,
#             'mo_dumps': mo_dumps}


# section question bank
@aiohttp_jinja2.template('bank.html')
@aiohttp_csrf.csrf_exempt
async def bank(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("""SELECT * FROM categories""")
            categories = await cur.fetchall()

    return {
        'page_title': "Question Bank",
        'csrf': csrf_token,
        'auth': auth, 'msg': '',
        'ENV': ENV,
        'this_page': request.rel_url,
        'yt_id': '6W_e7yQEzHo',
        'colors': request.app['colors'],
        'categories': categories,
        'cat_colors': {
            'performance': '#FF5B61',
            'peer-review': '#636F9A',
            'managed-up': '#29E7CD',
            'cqi': '#FF5BC3',
        }
    }


# section question bank
@aiohttp_jinja2.template('schedule.html')
@aiohttp_csrf.csrf_exempt
async def schedule(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    category_id = request.rel_url.query['category'] if 'category' in request.rel_url.query else None

    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("""SELECT * FROM categories""")
            categories = await cur.fetchall()

            await cur.execute("""SELECT * FROM departments""")
            departments = await cur.fetchall()

            await cur.execute("""SELECT * FROM surveys1""")
            survey1 = await cur.fetchall()

            await cur.execute("SELECT * FROM surveys")
            surveys = await cur.fetchall()
            print(survey1)
            print('-------')
            print(surveys)

            await cur.execute("""SELECT * FROM users""")
            users = await cur.fetchall()

        async with conn.cursor(DictCursor) as cur:
            await cur.execute("""
                SELECT s.id, s.title, s.category, s.department, s.weekly, s.question_order, s.repeat, s.sent_count, s.receive_count, c.cat_name, c.cat_slug, DATE_FORMAT(start_date, '%m/%d/%Y') AS start_date, DATE_FORMAT(end_date, '%m/%d/%Y') AS end_date, TIME_FORMAT(send_at, '%h:%i %p') AS send_at, COUNT(q.id) AS question_count, DATEDIFF(NOW(), s.start_date) AS days_active
                FROM surveys1 AS s
                LEFT JOIN categories AS c
                ON s.category=c.id
                LEFT JOIN questions1 AS q
                ON q.category = c.id
                GROUP BY s.id
                ORDER BY id DESC
            """)
            surveys = await cur.fetchall()

    return {
        'page_title': "Surveys",
        'csrf': csrf_token,
        'auth': auth, 'msg': '',
        'ENV': ENV,
        'this_page': request.rel_url,
        'yt_id': '6W_e7yQEzHo',
        'colors': request.app['colors'],
        'cat_colors': {
            'performance': '#FF5B61',
            'peer-review': '#29E7CD',
            'managed-up': '#63FF5B',
            'cqi': '#FF5BC3',
        },
        'categories': categories,
        'departments': departments,
        'surveys': surveys,
        'category_id': category_id
    }


# section add question
@aiohttp_jinja2.template('questions.html')
@aiohttp_csrf.csrf_exempt
async def questions(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    category_slug = request.match_info['category_slug'] if 'category_slug' in request.match_info else None
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(
                """
                SELECT * FROM categories
                WHERE cat_slug = %s
                """, (category_slug))
            category = await cur.fetchone()

            await cur.execute(
                """
                SELECT * FROM questions1
                WHERE
                    questions1.category = %s
                """, (category['id'],))
            questions = await cur.fetchall()

    return {
        'page_title': "Question Bank",
        'csrf': csrf_token,
        'auth': auth, 'msg': '',
        'ENV': ENV,
        'this_page': request.rel_url,
        'yt_id': '6W_e7yQEzHo',
        'colors': request.app['colors'],
        'questions': questions,
        'category': category
    }


# section advanced
@aiohttp_jinja2.template('create.html')
@aiohttp_csrf.csrf_exempt
async def create(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=False)
    csrf_token = await aiohttp_csrf.generate_token(request)
    survey_id = request.match_info['survey_id'] if 'survey_id' in request.match_info else None
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("""SELECT * FROM categories""")
            categories = await cur.fetchall()
    hiyer_rating_form = HiyerRatingForm()
    hiyer_rating_js = hiyer_rating_form.render_js()
    return {
        'page_title': "Create Surveys",
        'csrf': csrf_token,
        'auth': auth,
        'msg': '',
        'ENV': ENV,
        'this_page': request.rel_url,
        'survey_id': survey_id,
        'categories': categories,
        'yt_id': 'k5KrxBwlHA0',
        'question_form_js': hiyer_rating_js
    }


@aiohttp_jinja2.template('spot.html')
@aiohttp_csrf.csrf_exempt
async def spot(request):
    auth = await init_auth(request, protect=False)
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    return {
        'page_title': "Spot",
        'csrf': csrf_token,
        'auth': auth,
        'msg': '',
        'ENV': ENV,
        'this_page': request.rel_url,
    }


@aiohttp_jinja2.template('edit_employee.html')
@aiohttp_csrf.csrf_exempt
async def edit_employee(request):
    auth = await init_auth(request, protect=False)
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    employee_id = request.match_info['employee_id'] if 'employee_id' in request.match_info else None

    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("""
                SELECT * FROM users WHERE id = %s AND NOT is_new_user
            """, employee_id)
            employee = await cur.fetchone()

            await cur.execute("""
                SELECT * FROM departments WHERE org = %s
            """, auth['org'])
            departments = await cur.fetchall()

    return {
        'page_title': "Edit Employee",
        'csrf': csrf_token,
        'auth': auth,
        'employee': employee,
        'departments': departments,
        'msg': '',
        'ENV': ENV,
        'this_page': request.rel_url,
    }


@aiohttp_jinja2.template('edit_employee.html')
@aiohttp_csrf.csrf_exempt
async def add_employee(request):
    auth = await init_auth(request, protect=False)
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)

    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("""
                SELECT * FROM departments WHERE org = %s
            """, auth['org'])
            departments = await cur.fetchall()

    return {
        'page_title': "Add Employee",
        'csrf': csrf_token,
        'auth': auth,
        'departments': departments,
        'msg': '',
        'ENV': ENV,
        'this_page': request.rel_url,
    }


# section response rate
@aiohttp_jinja2.template('response_rate.html')
@aiohttp_csrf.csrf_exempt
async def response_rate(request):
    # session = await init_session(request)
    auth = await init_auth(request, protect=True, permission='user')
    if not auth.is_employer:
        raise web.HTTPFound('/')
    if not auth.is_employer:
        raise web.HTTPFound('/')
    csrf_token = await aiohttp_csrf.generate_token(request)
    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute("""
                SELECT d.id, d.dept_name, IFNULL(SUM(s.receive_count) / SUM(s.sent_count) * 100, 0) AS response_rate, IFNULL(SUM(i.answer) / COUNT(i.answer) * 10, 0) AS peer_review
                FROM departments AS d
                LEFT JOIN surveys1 AS s
                ON d.id = s.department
                LEFT JOIN survey_invites1 AS i
                ON s.id = i.survey_id
                WHERE d.org = %s
                GROUP BY d.id
            """, (auth['org']))
            department_rates = await cur.fetchall()

            await cur.execute("""
                SELECT u.id, u.first_name, u.last_name, d.dept_name, IFNULL(COUNT(i.answer) / COUNT(i.id) * 100, 0) AS response_rate, IFNULL(SUM(i.answer) / COUNT(i.answer) * 10, 0) AS peer_review
                FROM users AS u
                LEFT JOIN survey_invites1 AS i
                ON i.user_id = u.id
                LEFT JOIN departments AS d
                ON u.dept = d.id
                WHERE u.org = %s AND NOT u.is_employer AND NOT is_new_user
                GROUP BY u.id
            """, (auth['org']))
            employee_rates = await cur.fetchall()

    return {
        'page_title': "Your Stats",
        'csrf': csrf_token,
        'auth': auth,
        'ENV': ENV,
        'department_rates': department_rates,
        'employee_rates': employee_rates,
        'this_page': request.rel_url
    }


@aiohttp_csrf.csrf_exempt
async def export_csv(request):
    params = request.rel_url.query
    date_range_where = ''
    if params['date_range'] == 'custom':
        date_range_where = f"""AND Date(i.answered_at) >= DATE('{params['start_date']}') AND Date(i.answered_at) <= DATE('{params['end_date']}')"""
    elif params['date_range'] == '7d':
        date_range_where = 'AND Date(i.answered_at) >= DATE_SUB(DATE(NOW()), INTERVAL 7 DAY)'
    elif params['date_range'] == '1m':
        date_range_where = 'AND Date(i.answered_at) >= DATE_SUB(DATE(NOW()), INTERVAL 1 MONTH)'
    elif params['date_range'] == '3m':
        date_range_where = 'AND Date(i.answered_at) >= DATE_SUB(DATE(NOW()), INTERVAL 3 MONTH)'
    elif params['date_range'] == '1Y':
        date_range_where = 'AND Date(i.answered_at) >= DATE_SUB(DATE(NOW()), INTERVAL 1 YEAR)'

    async with request.app['mysql'].acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            if params['cat_id'] != '0':
                await cur.execute(f"""
                    SELECT * FROM questions1 WHERE category = {params['cat_id']} ORDER BY id
                """)
            else:
                await cur.execute(f"""
                    SELECT * FROM questions1 ORDER BY id
                """)
            questions = await cur.fetchall()

            if params['cat_id'] != '0':
                await cur.execute(f"""
                    SELECT ROUND(IFNULL(SUM(i.answer) / COUNT(i.id), 0)) AS average, DATE_FORMAT(i.answered_at, '%Y-%c-%e') AS date_info, i.question_id
                    FROM survey_invites1 AS i
                    LEFT JOIN surveys1 AS s
                    ON i.survey_id = s.id
                    WHERE s.category = {params['cat_id']} AND NOT ISNULL(i.answer) AND NOT ISNULL(s.id)
                    {date_range_where}
                    GROUP BY i.question_id, date_info
                    ORDER BY i.question_id
                """)
            else:
                await cur.execute(f"""
                    SELECT ROUND(IFNULL(SUM(i.answer) / COUNT(i.id), 0)) AS average, DATE_FORMAT(i.answered_at, '%Y-%c-%e') AS date_info, i.question_id
                    FROM survey_invites1 AS i
                    LEFT JOIN surveys1 AS s
                    ON i.survey_id = s.id
                    WHERE NOT ISNULL(i.answer) AND NOT ISNULL(s.id)
                    {date_range_where}
                    GROUP BY i.question_id, date_info
                    ORDER BY i.question_id
                """)
            anwsers  = await cur.fetchall()
    
    question_ids = []
    question_list = []

    for row in questions:
        question_ids.append(row['id'])
        question_list.append(row['question'])

    result = {}
    for row in anwsers:
        if row['date_info'] not in result:
            result[row['date_info']] = {}
        result[row['date_info']][row['question_id']] = row['average']
    
    text = ','.join(map(str, ['Timestamp'] + question_list))
    text += '\n'
    for date_info, data in result.items():
        row = ['0'] * len(question_ids)

        for question_id, score in data.items():
            row.insert(question_ids.index(question_id), score)

        text += ','.join(map(str, [date_info] + row))
        text += '\n'

    return web.Response(
        text = text,
        content_type = 'text/csv',
        headers = {'Content-Disposition': 'attachment;filename=score.csv'}
    )
