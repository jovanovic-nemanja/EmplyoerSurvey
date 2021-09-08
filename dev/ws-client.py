import asyncio

import ujson
from aiohttp import ClientSession, WSMsgType
from pyprnt import prnt


async def process_ws(_ws):
    # section process ws
    # await _ws.send_json({'cmd': 'ping'})
    async for msg in _ws:
        if msg.type == WSMsgType.TEXT:
            data = msg.data
            if hasattr(data, 'decode'):
                data = data.decode()
            try:
                j = ujson.loads(data)
                prnt(j)
            except ValueError as ex:
                print('Rcvd non-JSON:', data)
            '''if data:
                await _ws.send_str('pong')'''


async def task2(_ch):
    async for msg in _ch.iter(encoding="utf-8"):  # , decoder=json.loads
        print("receving", msg)
        """user_token = msg['token']
        if user_token in r_cons.keys():
            _ws = r_cons[user_token]
            await ws.send_json(msg)"""


async def main():
    # section main
    '''redis = await aioredis.create_redis_pool(
        'rediss://default:h9sbwltr2ot70ijf@redis-1-nyc3-do-user-8621886-0.b.db.ondigitalocean.com:25061'
    )'''
    session = ClientSession()
    ws = await session.ws_connect(
        'http://localhost:7081/ws'
    )
    # pubsub = Receiver(loop=asyncio.get_running_loop())
    # asyncio.ensure_future(sub_reader(pubsub, ws))
    # ch = await redis.subscribe(pubsub.channel('test'))
    
    coroutines = list()
    coroutines.append(process_ws(ws))
    # coroutines.append(task2(ch[0]))
    
    await asyncio.gather(*coroutines)
    while True:
        await asyncio.sleep(10)
        await ws.send_json({'cmd': 'ping'})
    """while True:
        msg = await ws.receive()
        if msg.type == aiohttp.MsgType.text:
            if msg.data == 'close':
                await ws.close()
                break
            else:
                ws.send_str(msg.data + '/answer')
        elif msg.tp == aiohttp.MsgType.closed:
            break
        elif msg.tp == aiohttp.MsgType.error:
            break"""


asyncio.run(main())
