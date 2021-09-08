import ujson
from aiomysql import DictCursor
from aiorun import run
from mo_dots import to_data

from common import ENV, aiohttp_fakeapp as fakeapp, log, mo_dumps, notify_user
from jobs.notifications import noti_main


async def cron_main(app=None):
    app = app if app is not None else await fakeapp()
    mysql = app['mysql']

    log.info('Starting survey cron processor.')

    async with mysql.acquire() as conn:
        async with conn.cursor(DictCursor) as cur:
            data = []

            await cur.execute("""
                SELECT * FROM surveys1 WHERE start_date <= DATE(NOW()) AND (ISNULL(end_date) OR end_date >= DATE(NOW())) AND send_at = TIME_FORMAT(NOW(), '%H:%i') AND (weekly = 'random' AND (FLOOR(RAND() * 10) % 2) = 1 OR weekly LIKE CONCAT('%', DATE_FORMAT(NOW(), '%a'), '%')) AND question_no < 10
            """)

            for cron_survey in await cur.fetchall():
                cron_survey = to_data(cron_survey)
                if (cron_survey.category_order):
                    await cur.execute("""
                        SELECT * FROM questions1 WHERE category=%s ORDER BY `order` ASC LIMIT %s, 1
                    """, (cron_survey.category, cron_survey.question_no))
                else:
                    await cur.execute("""
                        SELECT * FROM questions1 WHERE category=%s AND NOT id IN (SELECT question_id FROM survey_invites1 WHERE survey_id=%s) ORDER BY RAND() LIMIT 1
                    """, (cron_survey.category, cron_survey.id))
                question = await cur.fetchone()

                if not question:
                    return
                
                question = to_data(question)

                await cur.execute("""
                    SELECT id FROM users WHERE dept=%s AND NOT is_employer
                """, (cron_survey.department,))

                for user in await cur.fetchall():
                    user = to_data(user)
                    record = [user.id, cron_survey.id, question.id]
                    data.append(record)
                
                await cur.execute("""
                    UPDATE surveys1 SET question_no = question_no + 1 WHERE id = %s
                """, (cron_survey.id,))
                await conn.commit()
            
            if len(data):
                await cur.executemany(
                    "INSERT INTO survey_invites1 (user_id, survey_id, question_id)"
                    "values (%s, %s, %s)", data)
                await conn.commit()

                await noti_main(app)



            # await cur.execute(f"""
            #                     SELECT c.depts, s.survey_uuid, c.runs, c.id as cron_id, s.org, c.questions
            #                     FROM surveys s
            #                              JOIN crons c
            #                                   ON (JSON_SEARCH(c.surveys, 'all', s.survey_uuid) IS NOT NULL)
            #                                   OR (JSON_LENGTH(c.questions) > 0)
            #                     WHERE c.start_date < NOW()
            #                       AND c.end_date > NOW()
            #                     """)
            # for cron_survey in await cur.fetchall():
            #     cron_survey = to_data(cron_survey)
            #     this_run = cron_survey.runs + 1
            #     if 'questions' not in cron_survey or len(cron_survey.questions) == 0:
            #         # Survey-based. Skip users who have already received.
            #         await cur.execute(
            #             """
            #             SELECT user_id
            #             FROM survey_invites
            #             WHERE survey_uuid = %s
            #             AND run < %s
            #                UNION
            #             SELECT user_id
            #                 FROM answers
            #                 WHERE survey_uuid = %s
            #             """, (cron_survey.survey_uuid,
            #                   this_run,
            #                   cron_survey.survey_uuid,))
            #         usr_skips = await cur.fetchall()
            #         usr_skips = list(
            #             set([u['user_id'] for u in usr_skips]) if usr_skips is not None else [])
            #         await cur.execute(
            #             """
            #             SELECT id, dept
            #             FROM users
            #             WHERE (JSON_SEARCH(%s, 'one', id) IS NULL)
            #             AND (JSON_SEARCH(JSON_UNQUOTE(%s), 'one', dept) IS NOT NULL)
            #             AND org = %s
            #             """, (ujson.dumps(usr_skips),
            #                   mo_dumps(cron_survey.depts),
            #                   cron_survey.org,))
            #     else:
            #         for question in to_data(ujson.loads(cron_survey.questions)):
            #             # Questions-based.
            #             # Skip users who have already received or answered.
            #             await cur.execute(
            #                 """
            #                 SELECT *
            #                 FROM survey_questions WHERE id = %s
            #                 """, (question.id,))
            #             survey_question = await cur.fetchone()
            #             if survey_question is not None:
            #                 await cur.execute(
            #                     """
            #                     SELECT user_id
            #                     FROM survey_invites
            #                     WHERE (survey_uuid = %s AND qid = %s)
            #                     AND run < %s
            #                        UNION
            #                     SELECT user_id
            #                         FROM answers
            #                         WHERE survey_uuid = %s
            #                         AND qid = %s
            #                     """, (cron_survey.survey_uuid,
            #                           question.id,
            #                           this_run,
            #                           cron_survey.survey_uuid,
            #                           question.id,))
            #                 usr_skips = await cur.fetchall()
            #                 usr_skips = list(
            #                     set([u['user_id'] for u in usr_skips]) if usr_skips is not None else [])
            #                 await cur.execute(
            #                     """
            #                     SELECT id, dept
            #                     FROM users
            #                     WHERE (JSON_SEARCH(%s, 'one', id) IS NULL)
            #                     AND (JSON_SEARCH(JSON_UNQUOTE(%s), 'one', dept) IS NOT NULL)
            #                     AND org = %s
            #                     """, (ujson.dumps(usr_skips),
            #                           mo_dumps(cron_survey.depts),
            #                           cron_survey.org,))
            #     non_invited_users = await cur.fetchall()
            #     if non_invited_users is not None:
            #         for user in non_invited_users:
            #             # Process non-dupe survey invites.
            #             user = to_data(user)
            #             inv_loop = [None] if cron_survey.questions is None or len(
            #                 cron_survey.questions) == 0 else to_data(ujson.loads(cron_survey.questions))
            #             for q_or_none in inv_loop:
            #                 if q_or_none is None:
            #                     # Survey-based.
            #                     await cur.execute(
            #                         """
            #                         SELECT COUNT(*) as cnt
            #                         FROM survey_invites
            #                         WHERE user_id = %s
            #                         AND cron_id = %s
            #                         AND survey_uuid = %s
            #                         """, (user.id,
            #                               cron_survey.cron_id,
            #                               cron_survey.survey_uuid,))
            #                 else:
            #                     await cur.execute(
            #                         """
            #                         SELECT COUNT(*) as cnt
            #                         FROM survey_invites
            #                         WHERE user_id = %s
            #                         AND cron_id = %s
            #                         AND survey_uuid = %s
            #                         AND qid = %s
            #                         """, (user.id,
            #                               cron_survey.cron_id,
            #                               cron_survey.survey_uuid,
            #                               q_or_none.id,))
            #                 inv_dupe = await cur.fetchone()
            #                 if inv_dupe is not None and inv_dupe['cnt'] > 0:
            #                     await cur.execute(
            #                         """
            #                         SELECT c.*, n.datetime_stamp as noti_stamp
            #                         FROM notifications n
            #                         JOIN crons c
            #                         ON c.id = n.cron_id
            #                         WHERE n.cron_id = %s
            #                         AND n.user_id = %s
            #                         AND c.start_date < NOW()
            #                         AND c.end_date > NOW()
            #                         ORDER BY n.id DESC
            #                         LIMIT 1
            #                         """, (cron_survey.cron_id,
            #                               user.id,))
            #                     if last_noti := await cur.fetchone():
            #                         tdelta = last_noti['end_date'] - \
            #                             last_noti['start_date']
            #                         log.debug(f"Time delta {tdelta}")
            #                         continue
            #                 elif q_or_none is None:
            #                     # Process entire survey
            #                     await cur.execute(
            #                         """
            #                         INSERT INTO survey_invites
            #                         SET
            #                             user_id = %s,
            #                             cron_id = %s,
            #                             survey_uuid = %s
            #                         """, (user.id,
            #                               cron_survey.cron_id,
            #                               cron_survey.survey_uuid))
            #                     await notify_user(app,
            #                                       user.id,
            #                                       "New Hiyer Survey",
            #                                       f'You have a new Hiyer survey: {ENV.URL_PROTO}{ENV.SITE_DOMAIN}/s/{cron_survey.survey_uuid}',
            #                                       f'/s/{cron_survey.survey_uuid}',
            #                                       'ri:survey-fill')
            #                 else:
            #                     await cur.execute(
            #                         """
            #                         INSERT INTO survey_invites
            #                         SET
            #                             user_id = %s,
            #                             cron_id = %s,
            #                             survey_uuid = %s,
            #                             qid = %s
            #                         """, (user.id,
            #                               cron_survey.cron_id,
            #                               cron_survey.survey_uuid,
            #                               q_or_none.id,))
            #                     await notify_user(app,
            #                                       user.id,
            #                                       "New Hiyer Question",
            #                                       f'You have a new Hiyer question: {ENV.URL_PROTO}{ENV.SITE_DOMAIN}/q/{cron_survey.survey_uuid}/{q_or_none.id}',
            #                                       f'/s/{cron_survey.survey_uuid}',
            #                                       'ri:survey-fill')


if __name__ == '__main__':
    run(cron_main(), stop_on_unhandled_errors=True)
