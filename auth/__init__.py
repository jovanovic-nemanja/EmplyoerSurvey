import aiohttp_session
from aiohttp import web
from aiohttp_security import (
    authorized_userid,
    check_permission, )
from mo_dots import to_data

from common import referer_validator, unix_epoch
from sess import Alert, Session


async def init_auth(request, protect=False, permission='user'):
    user_data = None
    # if protect:
    #     user_data = await check_permission(request,
    #                                        permission)  # aiohttp_security/api.py return user from check_authorized
    user_data = await authorized_userid(request)
    # response = Response()
    session = Session(await aiohttp_session.get_session(request))
    alerter = Alert(web, session)
    alert = to_data(await session.get('alert'))  # await alerter.get_alert()
    alert_copy = {
        "message": alert.message,
        "style": alert.style
    }
    if alert is not None and request.app['last_alert'] != alert.message:
        request.app['last_alert'] = alert.message
        # await session.set('alert', None)
    else:
        await session.set('alert', None)

    #await session.set('alert', None)  # await alerter.get_alert()
    referer = await session.get('referer')
    rel_url = str(request.rel_url)
    this_path = rel_url if referer_validator(
        request.app['referer_regex'], rel_url
    ) else '/'
    await session.set('referer', this_path)
    
    last_action_date = await session.get('last_action_date')
    if last_action_date is not None:
        since_last_activity = unix_epoch() - last_action_date
    else:
        since_last_activity = 0
    await session.set('last_action_date', unix_epoch())
    
    username = False
    user_id = None
    is_superuser = None
    aff_id = None
    gravatar = None
    org = None
    dept = None
    mobile_number = None
    email_address = None
    company_name = None
    is_employer = None
    first_name = ''
    
    if user_data is not None:
        username = user_data['login']
        user_id = user_data['id']
        is_superuser = user_data['is_superuser']
        aff_id = user_data['aff_id']
        gravatar = user_data['gravatar']
        org = user_data['org']
        dept = user_data['dept']
        mobile_number = user_data['mobile_number']
        email_address = user_data['email_address']
        company_name = user_data['company_name']
        is_employer = user_data['is_employer']
        first_name = user_data['first_name']
    
    logged_in = False
    if username:
        logged_in = True
    return to_data({
        'logged_in': logged_in,
        'username': username,
        'user_id': user_id,
        'is_superuser': is_superuser,
        'referer': referer,
        'aff_id': aff_id,
        'gravatar': gravatar,
        'org': org,
        'dept': dept,
        'mobile_number': mobile_number,
        'email_address': email_address,
        'company_name': company_name,
        'is_employer': is_employer,
        'first_name': first_name,
        'alert': alert_copy,
        'session': session
    })
