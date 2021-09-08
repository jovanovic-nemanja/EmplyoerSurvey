import json
import aioredis
from collections import OrderedDict
import ujson


async def redis_connect(host, port):  # TODO: Create redis class from funcs.
    return await aioredis.create_redis(
        (host, port))  # password=CONFIG['redis']['password']


async def redis_pub(_redis, channel, message):
    return await _redis.publish(channel, ujson.dumps(message))


async def redis_close(_redis):
    _redis.close()
    await _redis.wait_closed()


class ReJSON:
    """Set commands mixin.

        For commands details see: https://oss.redislabs.com/redisjson/commands/
    """
    
    encoder = json
    decoder = json
    
    encode = getattr(encoder, 'dumps')
    decode = getattr(decoder, 'loads')
    
    def __init__(self, redis, encoder=None, decoder=None):
        self.redis = redis
        if encoder is not None:
            self.encoder = encoder
            self.encode = getattr(self.encoder, 'dumps')
        if decoder is not None:
            self.decoder = decoder
            self.decode = getattr(self.decoder, 'loads')
    
    async def set(self, key, path, jsonable, nx=False, xx=False):
        """
        Set the JSON value at ``key`` under the ``path`` to ``jsonable``
        ``nx`` if set to True, set ``value`` only if it does not exist
        ``xx`` if set to True, set ``value`` only if it exists
        """
        pieces = [self.encode(jsonable)]
        if nx and xx:
            raise Exception('nx and xx are mutually exclusive: use one, the '
                            'other or neither - but not both')
        elif nx:
            pieces.append('NX')
        elif xx:
            pieces.append('XX')
        return await self.redis.execute('JSON.SET', key, path, *pieces)
    
    async def get(self, key, *paths):
        """
        Get the object stored as a JSON value at ``key``
        ``paths`` is zero or more paths, and defaults to root path
        """
        if len(paths) == 0:
            paths = ['.']
        result = await self.redis.execute(b'JSON.GET', key, *paths)
        return self.decode(result) if result is not None else result
    
    async def delete(self, key, path='.'):
        """
        Deletes the JSON value stored at ``key`` under ``path``
        """
        return await self.redis.execute('JSON.DEL', key, path)
    
    async def mget(self, *keys, path='.'):
        """
        Gets the objects stored as JSON values under ``path`` from
        ``keys``
        """
        return await self.redis.execute('JSON.MGET', *keys, path)
    
    async def type(self, key, path='.'):
        """
        Gets the type of the JSON value under ``path`` from ``key``
        """
        return await self.redis.execute('JSON.TYPE', key, path)
    
    async def numincrby(self, key, path, number):
        """
        Increments the numeric (integer or floating point) JSON value under
        ``path`` at ``key`` by the provided ``number``
        """
        return await self.redis.execute('JSON.NUMINCRBY', key, path, number)
    
    async def nummultby(self, key, path, number):
        """
        Multiplies the numeric (integer or floating point) JSON value under
        ``path`` at ``key`` with the provided ``number``
        """
        return await self.redis.execute('JSON.NUMMULTBY', key, path, number)
    
    async def strappend(self, key, string, path='.'):
        """
        Appends to the string JSON value under ``path`` at ``key`` the
        provided ``string``
        """
        return await self.redis.execute('JSON.STRAPPEND', key, path, self.encode(string))
    
    async def strlen(self, key, path='.'):
        """
        Returns the length of the string JSON value under ``path`` at
        ``key``
        """
        return await self.redis.execute('JSON.STRLEN', key, path)
    
    async def arrappend(self, key, path, *jsonables):
        """
        Appends the objects ``args`` to the array under the ``path` in
        ``key``
        """
        pieces = []
        for o in jsonables:
            pieces.append(self.encode(o))
        return await self.redis.execute('JSON.ARRAPPEND', key, path, *pieces)
    
    async def arrindex(self, key, path, scalar, start=0, stop=-1):
        """
        Returns the index of ``scalar`` in the JSON array under ``path`` at
        ``key``. The search can be limited using the optional inclusive
        ``start`` and exclusive ``stop`` indices.
        """
        return self.redis.execute('JSON.ARRINDEX', key, path, self.encode(scalar), start, stop)
    
    async def arrinsert(self, key, path, index, *args):
        """
        Inserts the objects ``args`` to the array at index ``index`` under the
        ``path` in ``key``
        """
        pieces = []
        for o in args:
            pieces.append(self.encode(o))
        return self.redis.execute('JSON.ARRINSERT', key, path, index, *pieces)
    
    async def arrlen(self, key, path='.'):
        """
        Returns the length of the array JSON value under ``path`` at
        ``key``
        """
        return self.redis.execute('JSON.ARRLEN', key, path)
    
    async def arrpop(self, key, path='.', index=-1):
        """
        Pops the element at ``index`` in the array JSON value under ``path`` at
        ``key``
        """
        return self.redis.execute('JSON.ARRPOP', key, path, index)
    
    async def arrtrim(self, key, path, start, stop):
        """
        Trim the array JSON value under ``path`` at ``key`` to the
        inclusive range given by ``start`` and ``stop``
        """
        return self.redis.execute('JSON.ARRTRIM', key, path, start, stop)
    
    async def objkeys(self, key, path='.'):
        """
        Returns the key names in the dictionary JSON value under ``path`` at
        ``key``
        """
        return self.redis.execute('JSON.OBJKEYS', key, path)
    
    async def objlen(self, key, path='.'):
        """
        Returns the length of the dictionary JSON value under ``path`` at
        ``key``
        """
        return self.redis.execute('JSON.OBJLEN', key, path)


class Streams:
    # redis = None
    
    def __init__(self, _redis, _ws=None):
        self.redis = _redis
        self.last_id = None
        self.ws = _ws
        self.running = True
        self.max_len = 10000
    
    def dict_to_fields(self, _dict):
        # jo = dict_to_jo(_dict)
        fields = ""
        for key, val in _dict.items():
            fields += f"{key} {val} "
        return fields.rstrip()
    
    def decode_item(self, item):
        item_dict = dict(item[2])
        item_dict = {key.decode(): val.decode() for key, val in item_dict.items()}
        return ujson.loads(item_dict['json']) if 'json' in item_dict else False
    
    async def close(self):
        # self.loop_lock.release()
        self.running = False
        # await self.redis.close()
        # await self.redis.wait_closed()
    
    async def backlog(self, stream_id):
        pass
    
    async def add(self, stream_id, fields_dict):
        fields_dict = {
            'json': ujson.dumps(fields_dict)
        }
        item_id = await self.redis.xadd(str.encode(stream_id), fields_dict,
                                        max_len=self.max_len)
        return item_id.decode("utf-8")
    
    async def tail(self, expector, stream_id, last_id, callback):
        print('Tailing stream:', stream_id)
        while self.running:
            try:
                with await self.redis as _redis:
                    items = await _redis.xread([stream_id], latest_ids=[last_id], count=1)
                    for item in items:
                        print('Got stream ', stream_id, ' item:', item)
                        item_id = item[1].decode("utf-8")
                        last_id = item_id
                        item_dict = self.decode_item(item)
                        if not item_dict:
                            raise Exception('Error decoding stream JSON.')
                        # item_j = ujson.dumps(item_dict)
                        await callback(self.ws, expector, item_id, item_dict)
            except Exception as _e:
                print("Exception in stream tail:", _e)
