from concurrent.futures import ThreadPoolExecutor
import hashlib
from io import BytesIO
import json
import threading
import zipfile
from fastapi.testclient import TestClient
from medtestgen.main import create_app
from medtestgen.pipeline import build_dataset
from medtestgen.store import DatasetStore

def session(client):
    r=client.post('/api/session'); assert r.status_code==201
    return {'X-MedTestGen-Session':r.json()['token']}

def generate(client,headers,revision=0):
    return client.post('/api/datasets',headers=headers,json={
        'slices':1,'expected_revision':revision,'request_id':'request_123'})

def test_real_api_zip_and_integrity():
    store=DatasetStore()
    with TestClient(create_app(store)) as client:
        headers=session(client); result=generate(client,headers)
        assert result.status_code==201,result.text
        data=result.json()['dataset']; ident=data['dataset_id']
        assert data['eligible'] and data['report']['external_status']=='PASSED'
        assert client.get('/api/datasets/'+ident,headers=headers).json()['previews']['hl7'].startswith('MSH')
        response=client.get('/api/datasets/'+ident+'/zip',headers=headers)
        assert response.status_code==200
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            assert archive.testzip() is None
            assert set(archive.namelist())=={'dicom/CT_001.dcm','hl7/ORM_O01.hl7','fhir/bundle.json','manifest.json'}
            manifest=json.loads(archive.read('manifest.json'))
            assert manifest['dataset_id']==ident
        assert store.outgoing_bytes==0 and store.reserved_bytes==0
        assert response.headers['cache-control']=='no-store'
        assert client.get('/api/datasets/'+ident+'/zip').status_code==404
        assert client.get('/api/datasets/'+ident+'/zip',headers=session(client)).status_code==404

def test_direct_api_blocks_tampered_validation():
    store=DatasetStore()
    with TestClient(create_app(store)) as client:
        headers=session(client); result=generate(client,headers); ident=result.json()['dataset']['dataset_id']
        record=store.records[ident]
        for status in ('FAILED','NOT VERIFIED','WARNING'):
            record['report']['mandatory']['hl7']['status']=status
            r=client.get('/api/datasets/'+ident+'/zip',headers=headers)
            assert r.status_code==409 and r.headers['content-type'].startswith('application/json')
        record['report']['mandatory']['hl7']['status']='PASSED'
        record['confirmed_conformance_failure']=True
        assert client.get('/api/datasets/'+ident+'/zip',headers=headers).status_code==409

def test_generation_system_error_preserves_previous():
    count=0
    def builder(*args):
        nonlocal count
        count+=1
        if count==2: raise RuntimeError('PRIVATE TRACEBACK VALUE')
        return build_dataset(*args)
    store=DatasetStore()
    with TestClient(create_app(store,builder)) as client:
        headers=session(client); old=generate(client,headers).json()['dataset']['dataset_id']
        failed=generate(client,headers,1)
        assert failed.status_code==500 and 'PRIVATE' not in failed.text
        assert client.get('/api/session',headers=headers).json()['active_id']==old
        assert client.get('/api/datasets/'+old+'/zip',headers=headers).status_code==200
        assert store.reserved_bytes==0

def test_concurrent_requests_enforced_on_backend():
    entered=threading.Event(); resume=threading.Event()
    def slow(*args):
        entered.set(); assert resume.wait(10)
        return build_dataset(*args)
    with TestClient(create_app(builder=slow)) as client:
        headers=session(client)
        with ThreadPoolExecutor(1) as pool:
            future=pool.submit(generate,client,headers)
            try:
                assert entered.wait(5)
                assert generate(client,headers).status_code==409
                assert generate(client,session(client)).status_code==503
            finally: resume.set()
            assert future.result().status_code==201

def test_boundary_errors():
    with TestClient(create_app()) as client:
        headers=session(client)
        assert client.post('/api/datasets',headers=headers,content=b'x'*17000).status_code==413
        assert client.post('/api/datasets',headers=headers,json={'slices':11}).status_code==422
        assert client.post('/api/session',headers={'Origin':'http://evil.example'}).status_code==403
        assert client.post('/api/session',headers={'Host':'evil.example'}).status_code==403

def test_failed_regeneration_api_preserves_previous():
    count=0
    def builder(*args):
        nonlocal count
        record=build_dataset(*args); count+=1
        if count==2:
            record['report']['mandatory']['consistency']['status']='FAILED'
            record['zip_bytes']=None
        return record
    store=DatasetStore()
    with TestClient(create_app(store,builder)) as client:
        headers=session(client); old=generate(client,headers).json()['dataset']['dataset_id']
        response=generate(client,headers,1); assert response.status_code==200
        candidate=response.json()['dataset']
        assert candidate['state']=='failed' and not candidate['eligible']
        assert response.json()['session']['active_id']==old
        assert client.get('/api/datasets/'+candidate['dataset_id']+'/zip',headers=headers).status_code==409
        assert client.get('/api/datasets/'+old+'/zip',headers=headers).status_code==200


def test_known_expired_api_410():
    now=[0]; store=DatasetStore(clock=lambda:now[0])
    with TestClient(create_app(store)) as client:
        headers=session(client); ident=generate(client,headers).json()['dataset']['dataset_id']
        now[0]=1800; store.cleanup()
        assert client.get('/api/datasets/'+ident,headers=headers).status_code==410
        assert client.get('/api/datasets/'+ident+'/zip',headers=headers).status_code==410
        assert client.get('/api/datasets/not-known',headers=headers).status_code==404
