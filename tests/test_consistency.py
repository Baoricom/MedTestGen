from io import BytesIO
import json
import pytest
import pydicom
from medtestgen.models import GenerateRequest, make_scenario
from medtestgen.generators.dicom_ct import generate_ct
from medtestgen.generators.hl7_order import generate_hl7
from medtestgen.generators.fhir_bundle import generate_fhir
from medtestgen.validation.consistency import validate_consistency
from medtestgen.validation.hl7 import validate_hl7
from medtestgen.validation.fhir import validate_fhir

def outputs(**kwargs):
    s=make_scenario(GenerateRequest(**kwargs))
    return generate_ct(s),generate_hl7(s),generate_fhir(s)

@pytest.mark.parametrize('count',range(1,11))
def test_consistent(count):
    assert validate_consistency(*outputs(slices=count))['status']=='PASSED'

def test_unicode_and_escaping():
    d,h,f=outputs(patient_name='ТЕСТ&СЕМЬЯ^АЛЕКС',description='CT & head | phantom ^ test ~')
    assert b'\\F\\' in h and b'\\S\\' in h and b'\\T\\' in h and b'\\R\\' in h
    assert validate_hl7(h)['status']=='PASSED'
    assert validate_fhir(f)['status']=='PASSED'
    assert validate_consistency(d,h,f)['status']=='PASSED'

@pytest.mark.parametrize('field',['PatientID','AccessionNumber','StudyInstanceUID',
    'SeriesInstanceUID','SOPInstanceUID','StudyDescription','PatientBirthDate','PatientSex'])
def test_dicom_mismatch(field):
    d,h,f=outputs(slices=2)
    ds=pydicom.dcmread(BytesIO(d[1]))
    replacement='1.2.3' if 'UID' in field else '20000101' if field=='PatientBirthDate' else 'M' if field=='PatientSex' else 'DIFFERENT'
    setattr(ds,field,replacement)
    stream=BytesIO(); pydicom.dcmwrite(stream,ds,enforce_file_format=True)
    d[1]=stream.getvalue()
    assert validate_consistency(d,h,f)['status']=='FAILED'

@pytest.mark.parametrize('old,new',[(b'SYN-001',b'OTHER'),(b'SYN-ACC-001',b'ACC-OTHER'),
    (b'CT_SYNTHETIC',b'OTHER_PROC'),(b'CT Head',b'Other Study'),(b'MEDTESTGEN^MR',b'OTHER^MR')])
def test_hl7_mismatch(old,new):
    d,h,f=outputs()
    assert validate_consistency(d,h.replace(old,new),f)['status']=='FAILED'

def test_fhir_uid_mismatch():
    d,h,f=outputs()
    b=json.loads(f)
    study=next(e['resource'] for e in b['entry'] if e['resource']['resourceType']=='ImagingStudy')
    study['series'][0]['instance'][0]['uid']='1.2.3'
    assert validate_consistency(d,h,json.dumps(b).encode())['status']=='FAILED'

@pytest.mark.parametrize('target',['reference','timestamp'])
def test_link_and_time_mismatch(target):
    d,h,f=outputs()
    b=json.loads(f)
    order=next(e['resource'] for e in b['entry'] if e['resource']['resourceType']=='ServiceRequest')
    if target=='reference': order['subject']['reference']='urn:uuid:other'
    else: order['authoredOn']='2000-01-01T00:00:00Z'
    assert validate_consistency(d,h,json.dumps(b).encode())['status']=='FAILED'
