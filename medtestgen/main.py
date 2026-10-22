"""Local single-worker HTTP app. Generated content is never logged or persisted."""
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import re
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field, constr

from . import config
from .models import GenerateRequest
from .scenario import defaults, random_patient
from .store import DatasetStore, StoreError
from .pipeline import build_dataset
from .validation.windows_temp import cleanup_abandoned

class LeasedResponse(Response):
    def __init__(self,body,release,**kwargs):
        super().__init__(body,**kwargs)
        self.release=release
    async def __call__(self,scope,receive,send):
        try: await super().__call__(scope,receive,send)
        finally: self.release()
class DatasetRequest(GenerateRequest):
    expected_revision:int=Field(...,ge=0)
    request_id:constr(regex=r'^[A-Za-z0-9_-]{8,64}$')

class LocalBoundary:
    """Enforce body size while receiving, rather than trusting Content-Length."""
    def __init__(self,app): self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        original_send=send
        async def secure_send(event):
            if event['type']=='http.response.start':
                event['headers']=list(event.get('headers',[]))+[
                    (b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff'),
                    (b'referrer-policy',b'no-referrer'),
                    (b'content-security-policy',b"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'")]
            await original_send(event)
        send=secure_send
        headers={k.lower():v for k,v in scope['headers']}
        origin=headers.get(b'origin')
        host=headers.get(b'host',b'')
        valid_host=re.fullmatch(rb'(?:127\.0\.0\.1|localhost|testserver)(?::\d+)?',host)
        if not valid_host or (origin and origin!=b'http://'+host):
            return await JSONResponse({'code':'ORIGIN_DENIED','message':'Use the local application origin.'},403)(scope,receive,send)
        if scope['method'] in ('POST','PUT','PATCH'):
            body=bytearray()
            while True:
                event=await receive()
                if event['type']=='http.disconnect': return
                chunk=event.get('body',b'')
                if len(body)+len(chunk)>config.REQUEST_LIMIT:
                    return await JSONResponse({'code':'INPUT_TOO_LARGE','message':'Request exceeds 16 KiB.'},413)(scope,receive,send)
                body.extend(chunk)
                if not event.get('more_body'): break
            delivered=False
            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered=True
                    return {'type':'http.request','body':bytes(body),'more_body':False}
                return await receive()
            await self.app(scope,replay,send)
        else: await self.app(scope,receive,send)

def create_app(store=None,builder=None):
    store=store or DatasetStore(); builder=builder or build_dataset
    @asynccontextmanager
    async def lifespan(app):
        app.state.cleanup_issues=cleanup_abandoned()
        async def sweep():
            while True:
                await asyncio.sleep(config.CLEANUP_SECONDS)
                store.cleanup()
        task=asyncio.create_task(sweep())
        try: yield
        finally:
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass
    app=FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    app.state.store=store
    app.add_middleware(LocalBoundary)
    @app.exception_handler(StoreError)
    async def store_error(request,exc):
        return JSONResponse({'code':exc.code,'message':exc.message},exc.status)
    @app.exception_handler(RequestValidationError)
    async def bad_input(request,exc):
        fields=[{'field':'.'.join(str(x) for x in e['loc']),'reason':e['msg']} for e in exc.errors()]
        return JSONResponse({'code':'INVALID_INPUT','message':'Check the highlighted input fields.','fields':fields},422)
    def token(request):
        value=request.headers.get('X-MedTestGen-Session','')
        if len(value)!=43 or not re.fullmatch(r'[A-Za-z0-9_-]+',value):
            raise StoreError(404,'SESSION_NOT_FOUND','Session unavailable. Start a new session.')
        return value
    def leased(result,status=200,media_type='application/json',headers=None):
        body,release=result
        return LeasedResponse(body,release,status_code=status,media_type=media_type,headers=headers)
    @app.post('/api/session',status_code=201)
    def new_session(): return {**store.new_session(),'defaults':defaults()}
    @app.get('/api/session')
    def get_session(request:Request): return store.session(token(request))
    @app.get('/api/patient/random')
    def randomize(request:Request):
        store.session(token(request)); return random_patient()
    @app.post('/api/datasets')
    def generate(body:DatasetRequest,request:Request):
        owner=token(request)
        ticket=store.begin(owner,body.expected_revision,body.request_id)
        try:
            inputs=GenerateRequest(**body.dict(exclude={'expected_revision','request_id'}))
            record=builder(inputs,ticket.dataset_id,ticket.created_at,ticket.expires_at)
            promoted=store.finish(ticket,record)
        except StoreError: raise
        except Exception:
            raise StoreError(500,'GENERATION_ERROR','Generation could not complete. Previous results are preserved; try again.')
        finally: store.abort(ticket)
        return leased(store.view(owner,ticket.dataset_id,with_session=True),201 if promoted else 200)
    @app.get('/api/datasets/{ident}')
    def view(ident:str,request:Request): return leased(store.view(token(request),ident))
    @app.get('/api/datasets/{ident}/zip')
    def download(ident:str,request:Request):
        return leased(store.download(token(request),ident),media_type='application/zip',
                      headers={'Content-Disposition':'attachment; filename="MedTestGen.zip"'})
    static=Path(__file__).parent/'static'
    if static.exists():
        app.mount('/static',StaticFiles(directory=static),name='static')
        @app.get('/')
        def index(): return FileResponse(static/'index.html')
    return app

app=create_app()
