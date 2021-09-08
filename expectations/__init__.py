import asyncio
import random

import aiojobs


def eidgen():
    return str(random.random())


def in_dict_list(dict_list, dict_index, search_term):
    return next((i for i, item in enumerate(dict_list) if item[dict_index] == search_term), None)


class Expector:
    def __init__(self, scheduler=None):
        self.expecting = []
        self.expect_lock = asyncio.Lock()
        self.scheduler = scheduler
    
    async def expect(self, eid, callback):
        if self.scheduler is None:
            self.scheduler = await aiojobs.create_scheduler()
        try:
            await self.expect_lock.acquire()
            self.expecting.append({
                'eid': eid,
                'expected': None
            })
            index = len(self.expecting) - 1
        except:
            self.expect_lock.release()
            return False
        finally:
            self.expect_lock.release()
        
        async def listener(cb):
            while True:
                if self.expecting[index]['expected'] is not None:
                    result = cb(self.expecting[index]['expected'])
                    del self.expecting[index]
                    return result
                else:
                    await asyncio.sleep(1)
        
        await self.scheduler.spawn(listener(callback))
    
    async def check_expectations(self, eid, expected_obj):
        expect_index = in_dict_list(self.expecting, 'eid', eid)
        if expect_index is not None:
            self.expecting[expect_index]['expected'] = expected_obj
            return True
        else:
            return False
