from aioredis import create_redis_pool
#from common import ENV
from urllib.parse import urlparse
from pathlib import Path
from mo_dots import to_data
import ujson
import asyncio


async def go():
    redis_url = "redis://:@159.203.109.103:6379"  # "" # ENV.REDIS_URL
    redis = await create_redis_pool(redis_url,
                                    minsize=5,
                                    maxsize=20)
    counter = 0
    icons = []
    for file_path in Path("../api/collections-json/json").iterdir():
        counter += 1
        if counter == 1000:
            counter = 0
        lib_name = file_path.with_suffix('').name
        with open(file_path) as lib_file:
            icolib = to_data(ujson.load(lib_file))
            for icon in icolib.icons:
                icons.append(icon)
                #redis.sadd(f"ico:{icolib}:{icon}", lib_name)

if __name__ == '__main__':
    asyncio.run(go())
