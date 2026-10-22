"""Single-process bounded RAM store; no dataset files, persistence or accounts."""
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import json
import secrets
import threading
import time
from . import config
from .export import eligible

class StoreError(Exception):
    def __init__(self,status,code,message):
        self.status,self.code,self.message=status,code,message
        super().__init__(message)

@dataclass(frozen=True)
class Ticket:
    token:str
    revision:int
    request_id:str
    dataset_id:str
    deadline:float
    created_at:datetime
    expires_at:datetime

class DatasetStore:
    def __init__(self,clock=time.monotonic,ttl=config.TTL_SECONDS,
                 budget=config.MEMORY_BUDGET,record_limit=config.RECORD_LIMIT,
                 reservation=config.GENERATION_RESERVATION):
        self.clock,self.ttl,self.budget=clock,ttl,budget
        self.record_limit,self.reservation=record_limit,reservation
        self.lock=threading.RLock()
        self.sessions={}; self.records={}; self.tombstones=OrderedDict()
        self.retained_bytes=0; self.reserved_bytes=0; self.outgoing_bytes=0
        self.generation=None

    @property
    def accounted_bytes(self):
        return self.retained_bytes+self.reserved_bytes+self.outgoing_bytes

    def _remove(self,ident,expired=False):
        record=self.records.pop(ident,None)
        if record is None: return
        self.retained_bytes-=record['size_bytes']
        owner=record['_owner']
        session=self.sessions.get(owner)
        if session:
            for key in ('active_id','failed_id'):
                if session[key]==ident: session[key]=None
        if expired:
            self.tombstones[ident]=(owner,self.clock()+self.ttl)
            while len(self.tombstones)>config.TOMBSTONE_LIMIT:
                self.tombstones.popitem(last=False)

    def cleanup(self):
        with self.lock:
            now=self.clock()
            for ident,record in list(self.records.items()):
                if now>=record['_deadline']: self._remove(ident,expired=True)
            for ident,(_,deadline) in list(self.tombstones.items()):
                if now>=deadline: del self.tombstones[ident]
            for token,s in list(self.sessions.items()):
                if not s['busy'] and not s['active_id'] and not s['failed_id'] and now-s['last_activity']>=self.ttl and not any(owner==token for owner,_ in self.tombstones.values()):
                    del self.sessions[token]

    def _session(self,token):
        session=self.sessions.get(token)
        if session is None: raise StoreError(404,'SESSION_NOT_FOUND','Session unavailable. Start a new session.')
        session['last_activity']=self.clock()
        return session

    def new_session(self):
        with self.lock:
            self.cleanup()
            if len(self.sessions)>=config.SESSION_LIMIT:
                raise StoreError(503,'CAPACITY','Session capacity reached. Try again later.')
            token=secrets.token_urlsafe(32)
            self.sessions[token]={'revision':0,'busy':False,'request_id':None,
                'active_id':None,'failed_id':None,'last_activity':self.clock()}
            return {'token':token,**self.session(token)}

    def session(self,token):
        with self.lock:
            # Touch an existing session before pruning idle sessions, retaining known-expiry semantics.
            s=self._session(token)
            self.cleanup()
            return {key:s[key] for key in ('revision','busy','request_id','active_id','failed_id')}

    def begin(self,token,revision,request_id):
        with self.lock:
            s=self._session(token); self.cleanup()
            if s['busy'] or s['revision']!=revision:
                raise StoreError(409,'STALE_OR_BUSY','Generation already running or session changed. Refresh session state.')
            if self.generation or self.accounted_bytes+self.reservation>self.budget:
                raise StoreError(503,'CAPACITY','Generation capacity reached. Existing results are preserved; try again later.')
            now=datetime.now(timezone.utc)
            s['revision']+=1; s['busy']=True; s['request_id']=request_id
            ticket=Ticket(token,s['revision'],request_id,secrets.token_urlsafe(32),
                          self.clock()+self.ttl,now,now+timedelta(seconds=self.ttl))
            self.generation=ticket; self.reserved_bytes=self.reservation
            return ticket

    def abort(self,ticket):
        with self.lock:
            if self.generation!=ticket: return
            s=self.sessions.get(ticket.token)
            if s: s['busy']=False
            self.generation=None; self.reserved_bytes=0

    def finish(self,ticket,record):
        with self.lock:
            try:
                if self.generation!=ticket:
                    raise StoreError(409,'STALE_GENERATION','Generation is no longer current.')
                self.cleanup(); s=self._session(ticket.token)
                if self.clock()>=ticket.deadline:
                    raise StoreError(410,'EXPIRED','Generation expired. Generate again.')
                if record['dataset_id']!=ticket.dataset_id:
                    raise StoreError(500,'GENERATION_ERROR','Dataset identity mismatch.')
                size=record['size_bytes']
                if size>self.record_limit or size>self.reservation or size<0:
                    raise StoreError(503,'CAPACITY','Generated dataset exceeded memory limits. Previous result is preserved.')
                success=eligible(record)
                record.update(_owner=ticket.token,_deadline=ticket.deadline,
                              state='active' if success else 'failed')
                # All fallible validation/preparation precedes this synchronized pointer switch.
                previous=s['active_id'] if success else s['failed_id']
                self.records[ticket.dataset_id]=record; self.retained_bytes+=size
                if previous: self._remove(previous)
                s['active_id' if success else 'failed_id']=ticket.dataset_id
                return success
            finally:
                self.abort(ticket)

    def _record(self,token,ident):
        self._session(token); self.cleanup()
        record=self.records.get(ident)
        if record is None or record['_owner']!=token:
            if ident in self.tombstones and self.tombstones[ident][0]==token:
                raise StoreError(410,'EXPIRED','Dataset expired. Generate again.')
            raise StoreError(404,'NOT_FOUND','Dataset unavailable. Generate again.')
        return record

    def _public(self,record):
        allowed=eligible(record) and record['state']=='active'
        return {'dataset_id':record['dataset_id'],'created_at':record['created_at'],
            'expires_at':record['expires_at'],'state':record['state'],
            'eligible':allowed,'previews':record['previews'],'report':record['report'],
            'expected_instances':record['expected_instances']}

    def _lease(self,body):
        if self.accounted_bytes+len(body)>self.budget:
            raise StoreError(503,'CAPACITY','Download capacity reached. Try again later.')
        amount=len(body); self.outgoing_bytes+=amount
        released=False
        def release():
            nonlocal released
            with self.lock:
                if not released:
                    self.outgoing_bytes-=amount; released=True
        return body,release

    def view(self,token,ident,with_session=False):
        with self.lock:
            record=self._record(token,ident)
            # Reserve worst-case serialized preview space before allocating a response.
            if self.accounted_bytes+self.record_limit>self.budget:
                raise StoreError(503,'CAPACITY','Preview capacity reached. Try again later.')
            data=self._public(record)
            if with_session: data={'dataset':data,'session':self.session(token)}
            body=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode('utf-8')
            if len(body)>self.record_limit: raise StoreError(503,'CAPACITY','Preview exceeds memory limit.')
            return self._lease(body)

    def download(self,token,ident):
        with self.lock:
            record=self._record(token,ident)
            if record['state']!='active' or not eligible(record):
                raise StoreError(409,'VALIDATION_BLOCKED','ZIP blocked: required validation or file completeness failed.')
            return self._lease(record['zip_bytes'])
