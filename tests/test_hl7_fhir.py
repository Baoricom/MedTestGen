import json
import pytest
from medtestgen.models import GenerateRequest, make_scenario
from medtestgen.generators.hl7_order import generate_hl7
from medtestgen.generators.fhir_bundle import generate_fhir
from medtestgen.validation.hl7 import validate_hl7
from medtestgen.validation.fhir import validate_fhir

@pytest.mark.parametrize('sex',['M','F','O','U'])
@pytest.mark.parametrize('count',[1,5,10])
def test_linked_formats(sex,count):
    s=make_scenario(GenerateRequest(sex=sex,slices=count))
    assert validate_hl7(generate_hl7(s))['status']=='PASSED'
    assert validate_fhir(generate_fhir(s))['status']=='PASSED'

def test_hl7_profile_does_not_accept_missing_obr_or_procedure():
    p=generate_hl7(make_scenario(GenerateRequest()))
    assert validate_hl7(p.split(b'OBR')[0])['status']=='FAILED'
    assert validate_hl7(p.replace(b'CT_SYNTHETIC^CT Head^99MEDTESTGEN',b''))['status']=='FAILED'
    assert validate_hl7(p.replace(b'|2.5.1|',b'|2.4|'))['status']=='FAILED'

@pytest.mark.parametrize('mutation',['reference','count','uid','status','bundle','duplicate'])
def test_fhir_corruption(mutation):
    b=json.loads(generate_fhir(make_scenario(GenerateRequest())))
    study=next(e['resource'] for e in b['entry'] if e['resource']['resourceType']=='ImagingStudy')
    if mutation=='reference': study['subject']['reference']='urn:uuid:missing'
    if mutation=='count': study['numberOfInstances']=20
    if mutation=='uid': study['series'][0]['instance'][0]['uid']='bad-uid'
    if mutation=='status': study['status']='invented'
    if mutation=='bundle': b['type']='transaction'
    if mutation=='duplicate': b['entry'][1]['fullUrl']=b['entry'][0]['fullUrl']
    assert validate_fhir(json.dumps(b).encode())['status']=='FAILED'

@pytest.mark.parametrize('value',[None,123,True,[],{}])
def test_fhir_bad_scalar_never_raises(value):
    b=json.loads(generate_fhir(make_scenario(GenerateRequest())))
    patient=b['entry'][0]['resource']
    patient['id']=value
    assert validate_fhir(json.dumps(b).encode())['status']=='FAILED'
