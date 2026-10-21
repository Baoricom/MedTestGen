from io import BytesIO
import pytest
import pydicom
from medtestgen.models import GenerateRequest, make_scenario
from medtestgen.generators.dicom_ct import generate_ct
from medtestgen.validation.dicom_readback import validate_ct

@pytest.mark.parametrize('count',range(1,11))
def test_study(count):
    scenario=make_scenario(GenerateRequest(slices=count))
    payloads=generate_ct(scenario)
    assert validate_ct(payloads,scenario)['status']=='PASSED'
    assert len(set(pydicom.dcmread(BytesIO(p)).SOPInstanceUID for p in payloads))==count

def test_corruption_detected():
    scenario=make_scenario(GenerateRequest(slices=1))
    ds=pydicom.dcmread(BytesIO(generate_ct(scenario)[0]))
    del ds.PixelSpacing
    buffer=BytesIO(); pydicom.dcmwrite(buffer,ds,enforce_file_format=True)
    assert validate_ct([buffer.getvalue()],scenario)['status']=='FAILED'

@pytest.mark.parametrize('values',[{'slices':0},{'slices':11},{'slices':True},
    {'slices':1.2},{'accession':'A'*17},{'mrn':'A|B'},{'patient_name':'A^B^C'}])
def test_bad_inputs(values):
    with pytest.raises(ValueError): GenerateRequest(**values)

def test_unicode_unknown_sex():
    scenario=make_scenario(GenerateRequest(patient_name='ТЕСТ^АЛЕКС',slices=1))
    ds=pydicom.dcmread(BytesIO(generate_ct(scenario)[0]))
    assert str(ds.PatientName)=='ТЕСТ^АЛЕКС'
    assert ds.PatientSex==''
