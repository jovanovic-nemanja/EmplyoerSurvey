import asyncio
import random
import socket
import sys
import traceback
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count
from pathlib import Path
from urllib.parse import urlparse

import aiohttp_jinja2
import aiomysql
import dill as pkl
import jinja2
# from aiohttp.abc import AbstractAsyncAccessLogger
# from aiologger import Logger
# from aiohttp.abc import AbstractAccessLogger
# import re
import ujson
from aiohttp import web
from aiohttp_security import SessionIdentityPolicy, setup as setup_security
from aiohttp_session import setup as setup_session
from aiohttp_session.redis_storage import RedisStorage
from aiomysql import DictCursor
from aioredis import create_redis_pool
from aiorun import run
from mo_dots import Data, to_data
from multidict import CIMultiDict
from passlib import pwd
from passlib.context import CryptContext
from twilio.rest import Client

from auth.policy import DBAuthorizationPolicy
from common import ENV, log
from globals import BASE_PATH, register_globals
from jobs.notifications import noti_main
from jobs.surveys import cron_main
from middlewares import setup_middlewares
from routes import Web
from routes.ws import listen_to_redis

CPU_COUNT = cpu_count()
sys.setrecursionlimit(999999)


class Tags:
    def __init__(self, app):
        self.lock = asyncio.Lock()
        self.queue = asyncio.Queue()
        app['tag_list'] = []
        app['dept_list'] = []
        self.app = app
        log.debug('tags initialized')
        
    async def add(self, tag):
        await self.queue.put(tag)
        log.debug(f"added tag '{tag}' to queue")
    
    async def get(self, tag_type='dept'):
        return await self.app['redis'].smembers(f"{tag_type}s")
        
    async def proc(self):
        while item := await self.queue.get():
            await self.app['redis'].sadd(f"{item.type}s", item.tag)
    
    async def stop(self):
        await self.queue.join()
        self.queue.task_done()


async def pub_dummy_data(app: web.Application) -> None:
    log.debug('Pump rand data')
    try:
        red = app['redis']
        while True:
            dummy_dat = [pwd.genphrase(length=7, wordset="bip39") for _ in range(5)]
            await red.publish_json("globe:surveys", dummy_dat)
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        log.debug('Redis task got cancelled error.')
    except Exception as ex:
        log.exception(ex)
    finally:
        log.debug("Cancel Redis listener: close connection...")
        # await red.unsubscribe(ch.name)
        await red.quit()
        log.debug("Redis connection closed.")


async def on_shutdown(app: web.Application) -> None:
    for ws in app["websockets"]:
        await ws.close(code=999, message="Server shutdown")


async def run_crons(app):
    while True:
        log.debug('Processing background jobs.')
        await cron_main(app)
        #await noti_main(app)
        await asyncio.sleep(60)


async def start_background_tasks(app: web.Application) -> None:
    app["redis_listener"] = asyncio.create_task(listen_to_redis(app))
    # app["redis_dummy"] = asyncio.create_task(pub_dummy_data(app))
    app["tags_proc"] = asyncio.create_task(app["tags"].proc())
    cron_runner = asyncio.create_task(run_crons(app))
    noti_runner = asyncio.create_task(noti_main(app))
    asyncio.gather(app["redis_listener"],
                   # app["redis_dummy"],
                   app["tags_proc"],
                   cron_runner,
                   noti_runner,
                   loop=asyncio.get_event_loop())


async def cleanup_background_tasks(app: web.Application) -> None:
    log.info("Cleanup background tasks...")
    app["redis_listener"].cancel()
    await app["redis_listener"]
    await app["tags"].stop()


async def goto(http_path, status=302):
    return web.Response(status=status, headers=CIMultiDict(
        location=http_path
    ))


def udumps(o, default=None):
    return ujson.dumps(o)


def shuffle(seq):
    result = list(seq)
    random.shuffle(result)
    return result


def mk_socket(host, port, reuseport=False):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if reuseport:
        SO_REUSEPORT = 15
        sock.setsockopt(socket.SOL_SOCKET, SO_REUSEPORT, 1)
    sock.bind((host, port))
    return sock


async def init():
    try:
        host = ENV.SITE_HOST
        port = ENV.PORT
        loop = asyncio.get_event_loop()
        
        app = web.Application()
        
        app['argon2'] = CryptContext(schemes=["argon2"])
        app['mysql'] = await aiomysql.create_pool(host=ENV.MYSQL_HOSTNAME, port=ENV.MYSQL_PORT,
                                                  user=ENV.MYSQL_USERNAME, password=ENV.MYSQL_PASSWORD,
                                                  db=ENV.MYSQL_DATABASE, loop=loop, autocommit=True)
        app['twilio'] = Client(ENV['SMS_TWILIO_ACCOUNT_SID'],
                               ENV['SMS_TWILIO_AUTH_TOKEN'])
        app['tags'] = Tags(app)
        app['last_alert'] = None
        app["websockets"] = []
        app["user_websockets"] = {}
        app["creator_cache"] = {}
        async with app['mysql'].acquire() as conn:
            async with conn.cursor(DictCursor) as cur:
                await cur.execute("SELECT * FROM surveys")
                surveys = await cur.fetchall()
                for survey in surveys:
                    if f"{survey['user_id']}" not in app['creator_cache']:
                        app["creator_cache"][f"{survey['user_id']}"] = {
                            'saves': {},
                            'draft': ''
                        }
                    app["creator_cache"][f"{survey['user_id']}"]['saves'][survey['survey_uuid']] = {
                        'id': survey['survey_uuid'],
                        'org': survey['org'],
                        'user_id': survey['user_id'],
                        'json': survey['survey_json'],
                        'title': survey['survey_title']
                    }
                log.info(f'Loaded {len(surveys)} surveys into the cache.')
        app.on_startup.append(start_background_tasks)
        app.on_cleanup.append(cleanup_background_tasks)
        app.on_shutdown.append(on_shutdown)
        app['colors'] = Data()
        with open('tag_colors.pkl', 'rb') as file:
            app['colors'].tags = pkl.load(file)
        # TODO: Add back: app['geo'] = geoip2.database.Reader(ENV.SITE_GEO_PATH)
        if ENV.SITE_DEBUG_TOOLBAR:
            import aiohttp_debugtoolbar
            aiohttp_debugtoolbar.setup(app)
        if ('REDIS_USERNAME', 'REDIS_PASSWORD') in ENV:
            redis_url = urlparse(ENV.REDIS_URL)
            redis_url = f"{redis_url.scheme}://{ENV.REDIS_USERNAME}:{ENV.REDIS_PASSWORD}@{redis_url.netloc}"
        else:
            redis_url = ENV.REDIS_URL
        log.info(f"Connecting redis: {redis_url}")
        app['redis_receivers'] = Data()
        app['redis'] = await create_redis_pool(redis_url,
                                               minsize=4,
                                               maxsize=50)
        # app['redis'] = await redc.create_redis_cluster([redis_url,])  #, minsize = 50, maxsize = 200
        '''app['redis'] = await aioredis_cluster.create_redis_cluster(
            startup_nodes=[redis_url]
        )'''
        log.debug("Loading icons from disk....")
        app['icons'] = Data()
        app['icon_libs'] = []
        app['ico_dex'] = Data()
        count = 0
        for file_path in Path("static/images/icons/iconify-json").iterdir():
            lib_name = file_path.with_suffix('').name
            with open(file_path) as lib_file:
                try:
                    icolib_j = ujson.load(lib_file)
                    icolib = to_data(icolib_j)
                except ValueError as ex:
                    log.warning(f"Couldn't open {file_path}. Skipping...")
                    continue
                for icon in icolib.icons:
                    count += 1
                    if icon[0] not in app['ico_dex']:
                        app['ico_dex'][icon[0]] = [icon]
                    else:
                        app['ico_dex'][icon[0]].append(icon)
                    if icon not in app['icons']:
                        app['icons'][icon].libs = [icolib]
                    else:
                        app['icons'][icon].libs.append(icolib)
                    app_icons = app['icons']
                    ico_dex = app['ico_dex']
                    #app['redis'].sadd(f"ico:{icolib}:{icon}", lib_name)
        log.info(f"Loaded {count} icons.")
        # app['icon_libs'].append(file_path.with_suffix('').name)
        # await app['redis'].sadd(f"icon_{icon_name}")
        
        loop = asyncio.get_event_loop()
        loop.set_debug(not ENV.IN_PRODUCTION)
        
        handlers = Web()
        handlers.setup_routes(app)
        # app['referer_regex'] = re.compile("^[a-zA-Z0-9/_]+$")
        app = await register_globals(app)
        
        setup_session(app, RedisStorage(app['redis'], cookie_name=ENV.SITE_COOKIE_NAME, httponly=True))
        setup_security(app,
                       SessionIdentityPolicy(),
                       DBAuthorizationPolicy(app['mysql']))
        setup_middlewares(app)
        aiohttp_jinja2.setup(app,
                             loader=jinja2.FileSystemLoader(str(f'{BASE_PATH}/templates')),
                             filters=[('shuffle', shuffle)])
        runner = web.AppRunner(app)
        
        await runner.setup()
        if ENV.SITE_USE_MULTITHREAD:
            sock = mk_socket(host, port, reuseport=True)
            srv = web.SockSite(runner, sock)
        else:
            srv = web.TCPSite(runner, host, port)
        await srv.start()
        log.info(f'Server started at http://{host}:{port}')
        return srv, app, runner
    except Exception as ex:
        traceback.print_exc()
        # await logger.shutdown()
        raise


def main():
    run(init(), use_uvloop=ENV.SITE_UVLOOP)  # stop_on_unhandled_errors=True


if __name__ == '__main__':
    if ENV.SITE_USE_MULTITHREAD:
        with ProcessPoolExecutor() as executor:
            for i in range(0, CPU_COUNT):
                executor.submit(main)
    else:
        main()
