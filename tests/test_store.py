from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
import pytest
from medtestgen.models import GenerateRequest
from medtestgen.pipeline import build_dataset
from medtestgen.store import DatasetStore,StoreError

class Clock:
    value=0
    def __call__(self): return self.value

@pytest.fixture
def template():
    now=datetime.now(timezone.utc)
    return build_dataset(GenerateRequest(slices=1),'test',now,now+timedelta(minutes=30))

def complete(store,token,template,failed=False):
    ticket=store.begin(token,store.session(token)['revision'],'request_123')
    record=deepcopy(template); record['dataset_id']=ticket.dataset_id
    if failed:
        record['report']['mandatory']['hl7']['status']='FAILED'
        record['zip_bytes']=None
    store.finish(ticket,record)
    return ticket

def view(store,token,ident):
    body,release=store.view(token,ident)
    try:return json.loads(body)
    finally:release()

def test_expiry_and_cleanup(template):
    clock=Clock(); store=DatasetStore(clock=clock); token=store.new_session()['token']
    t=complete(store,token,template)
    clock.value=1799; assert view(store,token,t.dataset_id)['eligible']
    clock.value=1800; store.cleanup()
    with pytest.raises(StoreError) as err: store.download(token,t.dataset_id)
    assert err.value.status==410
    assert not store.records and store.retained_bytes==0
    with pytest.raises(StoreError) as err: store.download(token,'unknown')
    assert err.value.status==404

def test_failed_regeneration_preserves_old_and_ttl(template):
    clock=Clock(); store=DatasetStore(clock=clock); token=store.new_session()['token']
    old=complete(store,token,template)
    clock.value=100; failed=complete(store,token,template,True)
    assert store.session(token)['active_id']==old.dataset_id
    assert store.records[old.dataset_id]['_deadline']==1800
    assert view(store,token,failed.dataset_id)['state']=='failed'
    with pytest.raises(StoreError): store.download(token,failed.dataset_id)
    body,release=store.download(token,old.dataset_id); assert body; release()
    failed2=complete(store,token,template,True)
    assert failed.dataset_id not in store.records
    assert store.session(token)['failed_id']==failed2.dataset_id
    clock.value=1800; store.cleanup()
    assert old.dataset_id not in store.records
    assert failed2.dataset_id in store.records

def test_success_atomic_replacement_and_outgoing_lease(template):
    store=DatasetStore(); token=store.new_session()['token']
    old=complete(store,token,template)
    body,release=store.download(token,old.dataset_id)
    assert store.outgoing_bytes==len(body)
    new=complete(store,token,template)
    assert old.dataset_id not in store.records
    assert store.session(token)['active_id']==new.dataset_id
    assert store.outgoing_bytes==len(body)
    release(); release(); assert store.outgoing_bytes==0

def test_abort_overlap_capacity_and_expiry_mid_attempt(template):
    clock=Clock(); store=DatasetStore(clock=clock); token=store.new_session()['token']
    old=complete(store,token,template)
    clock.value=1700; ticket=store.begin(token,1,'request_123')
    with pytest.raises(StoreError) as err: store.begin(token,1,'request_456')
    assert err.value.status==409
    token2=store.new_session()['token']
    with pytest.raises(StoreError) as err: store.begin(token2,0,'request_789')
    assert err.value.status==503
    clock.value=1800; store.abort(ticket); store.cleanup()
    assert old.dataset_id not in store.records
    assert store.reserved_bytes==0 and not store.session(token)['busy']
    ticket=store.begin(token,2,'request_abc'); clock.value=3600
    record=deepcopy(template); record['dataset_id']=ticket.dataset_id
    with pytest.raises(StoreError) as err: store.finish(ticket,record)
    assert err.value.status==410 and not store.records and store.reserved_bytes==0

def test_capacity_never_evicts_valid_data(template):
    store=DatasetStore(); token=store.new_session()['token']; old=complete(store,token,template)
    store.budget=store.retained_bytes+store.reservation-1
    with pytest.raises(StoreError) as err: store.begin(token,1,'request_abc')
    assert err.value.status==503 and old.dataset_id in store.records
    assert store.reserved_bytes==0

def test_restart_and_cross_session_ownership(template):
    store=DatasetStore(); token=store.new_session()['token']; t=complete(store,token,template)
    other=store.new_session()['token']
    with pytest.raises(StoreError) as err: store.download(other,t.dataset_id)
    assert err.value.status==404
    fresh=DatasetStore()
    with pytest.raises(StoreError) as err:fresh.download(token,t.dataset_id)
    assert err.value.status==404

def test_reconciliation_and_stale_revision(template):
    store=DatasetStore(); token=store.new_session()['token']; t=complete(store,token,template)
    assert store.session(token)['active_id']==t.dataset_id
    with pytest.raises(StoreError) as err:store.begin(token,0,'request_abc')
    assert err.value.status==409

def test_oversized_candidate_and_incomplete_zip_keep_old(template):
    store=DatasetStore(); token=store.new_session()['token']; old=complete(store,token,template)
    ticket=store.begin(token,1,'request_xyz')
    record=deepcopy(template); record['dataset_id']=ticket.dataset_id; record['size_bytes']=store.record_limit+1
    with pytest.raises(StoreError) as err:store.finish(ticket,record)
    assert err.value.status==503 and old.dataset_id in store.records and store.reserved_bytes==0
    ticket=store.begin(token,2,'request_abc')
    record=deepcopy(template); record['dataset_id']=ticket.dataset_id; record['zip_bytes']=None
    assert not store.finish(ticket,record)
    assert store.session(token)['active_id']==old.dataset_id


def test_tombstones_bounded_and_removed(template):
    clock=Clock(); store=DatasetStore(clock=clock,ttl=1); token=store.new_session()['token']
    t=complete(store,token,template)
    clock.value=1; store.cleanup(); assert t.dataset_id in store.tombstones
    clock.value=2; store.cleanup(); assert not store.tombstones and not store.sessions
