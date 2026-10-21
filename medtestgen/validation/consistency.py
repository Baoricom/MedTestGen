from io import BytesIO
import json
import pydicom
from .hl7 import extract_hl7, unescape

BASE='https://medtestgen.example/identifier/'

def validate_consistency(dicom, hl7, fhir):
    errors=[]
    def equal(actual,expected,field):
        if actual!=expected: errors.append({'field':field,'reason':'Cross-standard mismatch'})
    def identifier(resource,system):
        found=[i['value'] for i in resource.get('identifier',[]) if i.get('system')==system]
        if len(found)!=1: raise ValueError('Expected exactly one identifier: '+system)
        return found[0]
    try:
        ds=[pydicom.dcmread(BytesIO(p)) for p in dicom]
        if not ds: raise ValueError('DICOM study empty')
        first=ds[0]; h=extract_hl7(hl7)
        bundle=json.loads(fhir)
        resources={e['resource']['resourceType']:e['resource'] for e in bundle['entry']}
        patient=resources['Patient']; order=resources['ServiceRequest']; study=resources['ImagingStudy']
        p=h['PID']; o=h['ORC']; b=h['OBR']; series=study['series'][0]
        patient_url='urn:uuid:'+patient['id']
        equal(order['subject']['reference'],patient_url,'ServiceRequest.subject')
        equal(study['subject']['reference'],patient_url,'ImagingStudy.subject')
        equal(study['basedOn'],[{'reference':'urn:uuid:'+order['id']}],'ImagingStudy.basedOn')
        from datetime import datetime
        scenario_time=datetime.fromisoformat(order['authoredOn'].replace('Z','+00:00'))
        hl7_time=scenario_time.strftime('%Y%m%d%H%M%S+0000')
        equal(h['MSH'][6],hl7_time,'MSH-7')
        equal(o[9],hl7_time,'ORC-9')
        equal(study['started'],order['authoredOn'],'ImagingStudy.started')
        mrn=identifier(patient,BASE+'mrn'); accession=identifier(order,BASE+'accession')
        equal(identifier(study,BASE+'accession'),accession,'ImagingStudy.identifier.accession')
        equal(unescape(p[3].split('^')[0]),mrn,'PID-3.1')
        equal(p[3].split('^')[3:5],['MEDTESTGEN','MR'],'PID-3 authority/type')
        for field in (o[2],b[2]):
            equal(unescape(field.split('^')[0]),identifier(order,BASE+'placer-order'),'placer order')
            equal(field.split('^')[1],'MEDTESTGEN','placer authority')
        filler=identifier(order,BASE+'filler-order')
        equal(filler,accession,'filler/accession profile')
        for field in (o[3],b[3]):
            equal(unescape(field.split('^')[0]),filler,'filler order')
            equal(field.split('^')[1],'MEDTESTGEN','filler authority')
        equal(unescape(b[18]),accession,'OBR-18')
        description=order['code']['text']
        equal(unescape(b[4].split('^')[1]),description,'OBR-4.2')
        equal(b[4].split('^')[0],'CT_SYNTHETIC','OBR-4.1')
        equal(b[4].split('^')[2],'99MEDTESTGEN','OBR-4.3')
        equal(order['code']['coding'][0]['code'],'CT_SYNTHETIC','ServiceRequest.code')
        equal(study['description'],description,'ImagingStudy.description')
        equal(unescape(p[5].split('^')[0]),patient['name'][0]['family'],'PID-5 family')
        given=patient['name'][0].get('given',[])
        equal(unescape((p[5].split('^')+[''])[1]),given[0] if given else '','PID-5 given')
        equal(p[7],patient['birthDate'].replace('-',''),'PID-7')
        sex={'male':'M','female':'F','other':'O','unknown':'U'}[patient['gender']]
        equal(p[8],sex,'PID-8')
        for index,d in enumerate(ds):
            equal(d.PatientID,mrn,f'DICOM[{index}].PatientID')
            equal(str(d.StudyDate)+str(d.StudyTime)+str(d.TimezoneOffsetFromUTC),hl7_time,'DICOM study time')
            equal(d.IssuerOfPatientID,'MEDTESTGEN','DICOM issuer')
            equal(d.AccessionNumber,accession,'DICOM accession')
            equal(d.StudyDescription,description,'DICOM description')
            equal(str(d.PatientName).split('^')[0],patient['name'][0]['family'],'DICOM name family')
            equal((str(d.PatientName).split('^')+[''])[1],given[0] if given else '','DICOM name given')
            equal(str(d.PatientBirthDate),p[7],'DICOM birth date')
            equal(d.PatientSex,'' if sex=='U' else sex,'DICOM sex')
            equal('urn:oid:'+d.StudyInstanceUID,identifier(study,'urn:dicom:uid'),'Study UID')
            equal(d.SeriesInstanceUID,series['uid'],'Series UID')
            equal(d.FrameOfReferenceUID,first.FrameOfReferenceUID,'FrameOfReferenceUID')
            equal(d.Modality,series['modality']['code'],'Modality')
            instance=series['instance'][index]
            equal(d.SOPInstanceUID,instance['uid'],'SOP UID')
            equal('urn:oid:'+d.SOPClassUID,instance['sopClass']['code'],'SOP Class')
            equal(int(d.InstanceNumber),instance['number'],'Instance number')
        equal(len(ds),study['numberOfInstances'],'study count')
        equal(len(ds),series['numberOfInstances'],'series count')
        equal(len(ds),len(series['instance']),'instance list count')
        equal(len(set(d.SOPInstanceUID for d in ds)),len(ds),'unique SOP UIDs')
        equal(study['numberOfSeries'],1,'series count')
    except Exception as exc:
        errors.append({'field':'outputs','reason':str(exc)})
    return {'status':'FAILED' if errors else 'PASSED','findings':errors,
            'coverage':'Identifiers, demographics, order and instance metadata extracted from serialized outputs'}
