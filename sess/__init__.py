import uuid

import aiohttp_session
import ujson
from mo_dots import to_data


async def init_session(request):
    if session := await aiohttp_session.get_session(request):
        if sess := Session(session):
            await sess.get_all()
            if 'uuid' not in sess.data:
                session_uuid = str(uuid.uuid4()).replace('-', '')
                await sess.set('uuid', session_uuid)
                sess.data.uuid = session_uuid
            return sess
    return None


class Session:
    
    def __init__(self, session):
        self.sess = session
        self.data = None
    
    async def init_sess(self, request):
        self.sess = await aiohttp_session.get_session(request)
        
    async def get(self, getter, default=None):
        return self.sess[getter] if getter in self.sess and self.sess[getter] is not None else default
    
    async def set(self, setter, content):
        self.sess[setter] = content
        
    async def get_all(self):
        if self.sess is not None:
            if 'AIOHTTP_SECURITY' in self.sess._mapping:
                username = self.sess._mapping['AIOHTTP_SECURITY']
                dat = to_data(self.sess._mapping)
                dat.username = username
            else:
                dat = to_data(self.sess._mapping)
            self.data = dat or None
            return self.data


class Alert:
    def __init__(self, web, session):
        self.web = web
        self.sess = session
        
    async def set_alert(self, message, style):
        await self.sess.set('alert', {
            'message': message,
            'style': style
        })
        
    async def get_alert(self):
        alert = await self.sess.get('alert')
        await self.sess.set('alert', None)
        return alert
    
    async def alert(self, message, caller, style, in_place):
        await self.sess.set('alert', {
            'message': message,
            'style': style
        })
        if not in_place:
            raise self.web.HTTPFound(f'{caller}#alert')
        
    async def error(self, message, caller, in_place=False):
        await self.alert(f"<b>Error:</b> {message}", caller, 'danger', in_place)
        
    async def warn(self, message, caller, in_place=False):
        await self.alert(f"<b>Warning:</b> {message}", caller, 'warning', in_place)
        
    async def success(self, message, caller, in_place=False):
        await self.alert(message, caller, 'success', in_place)
        
    async def info(self, message, caller, in_place=False):
        await self.alert(message, caller, 'info', in_place)
        
    async def primary(self, message, caller, in_place=False):
        await self.alert(message, caller, 'primary', in_place)
    
    async def alert_patch(self, msg, lvl):
        pass
        
