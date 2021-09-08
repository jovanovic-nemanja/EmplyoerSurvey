import os

from globals import BASE_PATH
from routes.admin import admin_home, admin_users, admin_algo
from routes.api import list_surveys, list_users, do_add_company, do_update_employee, \
    do_invite_user, do_delete_employee, do_invite_employees
from routes.auth import do_forgot_password, do_login, do_logout, do_register, \
    forgot_password, jwt_token, login, register, register_employee, register_employer
from routes.debug import login_test
from routes.public import index, learn
from routes.user import create, orgs, user_settings, calendar, user_stats, dashboard, \
    answer, bank, create_simple, survey, schedule, questions, survey_stats, \
    question_stats, category_stats, spot, edit_employee, add_employee, response_rate, export_csv
from routes.ws import websocket_handler
from aiojobs.aiohttp import setup as setup_jobs


class Web(object):

    @staticmethod
    def setup_static_routes(app):
        app.router.add_static(
            '/', path=os.path.join(BASE_PATH, 'static'), name='static', show_index=False)

    def setup_routes(self, app):
        # Public routes
        app.router.add_get('/', index, name='index')

        # Public API routes
        app.router.add_post('/api/do_update_employee', do_update_employee)
        app.router.add_post('/api/do_delete_employee', do_delete_employee)
        app.router.add_post('/api/do_add_company', do_add_company)
        app.router.add_post('/api/do_invite_employees', do_invite_employees)
        app.router.add_get('/learn', learn)

        # Auth routes
        app.router.add_get('/login', login)
        app.router.add_post('/do_login', do_login)
        app.router.add_get('/join', register)
        app.router.add_get('/register_employee', register_employee)
        app.router.add_get('/i/{invite_code}', register_employee)
        app.router.add_get('/register_employer', register_employer)
        app.router.add_post('/do_register', do_register)
        app.router.add_get('/logout', do_logout)
        app.router.add_get('/token', jwt_token)
        app.router.add_get('/forgot_password', forgot_password)
        app.router.add_post('/do_forgot_password', do_forgot_password)
        app.router.add_get('/s/{survey_invite_id}', survey)
        app.router.add_get('/s', survey)

        # Admin routes
        app.router.add_get('/admin', admin_home)
        app.router.add_get('/admin/users', admin_users)
        app.router.add_get('/admin/algo', admin_algo)

        # Admin API routes
        app.router.add_get('/api/admin/list_users', list_users)
        app.router.add_get('/api/admin/surveys', list_surveys)

        # User routes
        app.router.add_get('/create_simple', create_simple)
        app.router.add_get('/create', create)
        app.router.add_get('/c/{survey_id}', create)
        app.router.add_get('/dash', dashboard)
        app.router.add_get('/org', orgs)
        app.router.add_get('/your/settings', user_settings)
        app.router.add_get('/your/calendar', calendar)
        app.router.add_get('/stats', user_stats)
        app.router.add_get('/answer', answer)
        app.router.add_get('/bank', bank)
        app.router.add_get('/schedule', schedule)
        app.router.add_get('/{category_slug}/questions', questions)
        app.router.add_get('/q/{survey_uuid}/{qid}', survey)
        app.router.add_get('/survey_stats/{survey_id}', survey_stats)
        app.router.add_get('/question_stats/{question_id}', question_stats)
        app.router.add_get('/category_stats/{category_id}', category_stats)
        app.router.add_get('/spot', spot)
        app.router.add_get('/employee/{employee_id}', edit_employee)
        app.router.add_get('/add_employee', add_employee)
        app.router.add_get('/response_rate', response_rate)
        app.router.add_get('/export_csv', export_csv)

        # Employer routes do_invite_user
        app.router.add_post('/do_invite_user', do_invite_user)

        # WS
        # add_routes([web.get('/ws', websocket_handler)])
        app.router.add_route('GET', '/ws', websocket_handler)

        # Testing & Debug
        # TODO: Remove this route
        app.router.add_get('/login-test', login_test)

        # static content
        self.setup_static_routes(app)

        setup_jobs(app)
