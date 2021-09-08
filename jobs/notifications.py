import asyncio
from inspect import currentframe, getframeinfo
from pathlib import Path

from mo_dots import to_data
import aiomysql
import ujson
import json
from aiomysql import DictCursor
from aiorun import run
from python_http_client import UnauthorizedError
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from twilio.rest import Client
from common import ENV, log, notify_user, linkify, aiohttp_fakeapp as fakeapp
from cron_descriptor import get_description, ExpressionDescriptor, Options, CasingTypeEnum, DescriptionTypeEnum
from bs4 import BeautifulSoup

'''filename = getframeinfo(currentframe()).filename
WORKING_DIR = Path(filename).resolve().parent'''


async def noti_main(app=None):
    log.info('Starting notifications processor.')
    app = app if app is not None else await fakeapp()
    mysql = app['mysql']
    async with mysql.acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            await cur.execute(f"""
                                SELECT *
                                FROM
                                    notifications n
                                JOIN users u
                                ON n.user_id = u.id
                                WHERE
                                    not n.sent
                                """)
            new_items = await cur.fetchall()
            if new_items is None or len(new_items) == 0:
                log.debug('No notifications to process at this time.')
                
            log.info(f"Processing {len(new_items)} alert items.")
            client = Client(ENV.SMS_TWILIO_ACCOUNT_SID, ENV.SMS_TWILIO_AUTH_TOKEN)
            sg = SendGridAPIClient(api_key=ENV.EMAIL_SENDGRID_KEY)
            for item in new_items:
                await cur.execute("""
                                    UPDATE
                                        notifications
                                    SET
                                        sent = 1
                                    WHERE
                                        id = %s
                                """, (item['id'],))
                try:
                    msg = item['msg']
                    if item['mobile_number'] is not None and len(item['mobile_number']) > 0:
                        sms_message = client.messages \
                            .create(
                            body=msg,
                            from_=ENV.SMS_TWILIO_NUMBER,
                            to=item['mobile_number']
                        )
                        log.debug(f"Twilio: Sent sms to {item['mobile_number']}; sid: {sms_message.sid}")
                    if item['email_address'] is not None and len(item['email_address']) > 0:
                        try:
                            email_message = Mail(
                                from_email=ENV.EMAIL_DEFAULT_SENDER,
                                to_emails=item['email_address'],
                                subject=f"{item['title']} - Hiyer",
                                html_content=linkify(msg))
                            response = sg.send(email_message)
                            log.debug(f"SendGrid: Sent email to {item['email_address']}; got response code: {response.status_code}")
                        except (UnauthorizedError, Exception) as ex:
                            log.warning('Unable to send email via sendgrid.', ex)
                except Exception as e:
                    log.exception(e)
                    

if __name__ == '__main__':
    run(noti_main(), stop_on_unhandled_errors=True)
