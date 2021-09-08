import ujson
import logging as log


class Streams:
    # redis = None
    
    def __init__(self, _redis, _ws=None, logger=log, debug=False):
        self.redis = _redis
        self.last_id = None
        self.ws = _ws
        self.running = True
        self.max_len = 10000
        self.log = logger
        self.debug = debug
    
    def dict_to_fields(self, _dict):
        print(type(_dict))
        # jo = dict_to_jo(_dict)
        fields = ""
        for key, val in _dict.items():
            fields += f"{key} {val} "
        return fields.rstrip()
    
    def decode_item(self, item):
        try:
            item_dict = dict(item[2])
            item_dict = {key.decode(): val.decode() for key, val in item_dict.items()}
            return ujson.loads(item_dict['json']) if 'json' in item_dict else False
        except ValueError as ex:
            self.log.warning('Error decoding stream item to json.')
            return None
    
    async def close(self):
        # self.loop_lock.release()
        self.running = False
        # await self.redis.close()
        # await self.redis.wait_closed()
    
    async def backlog(self, stream_id):
        pass
    
    async def add(self, stream_id, fields_dict):
        # print(OrderedDict(fields_dict))
        fields_dict = {
            'json': ujson.dumps(fields_dict)
        }
        item_id = await self.redis.xadd(str.encode(stream_id), fields_dict,
                                        max_len=self.max_len)
        return item_id.decode("utf-8")
    
    async def tail(self, expector, stream_id, last_id, callback):
        self.log.info('Tailing stream:', stream_id)
        while self.running:
            try:
                with await self.redis as _redis:
                    items = await _redis.xread([stream_id], latest_ids=[last_id], count=1)
                    for item in items:
                        self.log.debug('Got stream ', stream_id, ' item:', item)
                        item_id = item[1].decode("utf-8")
                        last_id = item_id
                        item_dict = self.decode_item(item)
                        if item_dict is None:
                            if self.debug:
                                raise ValueError('Error decoding stream item to json.')
                            continue
                        await callback(self.ws, expector, item_id, item_dict)
                        # print(item_id, item_j)
            except Exception as _e:
                print("Exception in stream tail:", _e)
