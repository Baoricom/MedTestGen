from io import BytesIO
import pydicom
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian

def validate_ct(payloads, scenario):
    errors = []
    def check(condition, field, reason):
        if not condition:
            errors.append({'standard':'DICOM','field':field,'reason':reason})
    check(len(payloads)==scenario.request.slices, 'count', 'Unexpected slice count')
    seen = set()
    for index, payload in enumerate(payloads):
        try:
            ds=pydicom.dcmread(BytesIO(payload))
            check(ds.SOPClassUID==CTImageStorage, 'SOPClassUID','Expected CT Image Storage')
            check(ds.file_meta.TransferSyntaxUID==ExplicitVRLittleEndian,'TransferSyntaxUID','Unexpected syntax')
            check(ds.SOPInstanceUID==ds.file_meta.MediaStorageSOPInstanceUID,'SOPInstanceUID','File meta mismatch')
            check(ds.file_meta.MediaStorageSOPClassUID==ds.SOPClassUID,'SOPClassUID','File meta mismatch')
            check(ds.SOPInstanceUID not in seen,'SOPInstanceUID','Duplicate UID')
            seen.add(ds.SOPInstanceUID)
            for field, expected in dict(StudyInstanceUID=scenario.study_uid,
                SeriesInstanceUID=scenario.series_uid,FrameOfReferenceUID=scenario.frame_uid,
                PatientID=scenario.request.mrn,AccessionNumber=scenario.request.accession,
                Modality='CT',Rows=512,Columns=512,BitsAllocated=16,BitsStored=16,
                HighBit=15,PixelRepresentation=0,SamplesPerPixel=1,
                PhotometricInterpretation='MONOCHROME2',RescaleSlope=1,RescaleIntercept=-1024,
                SliceThickness=1,InstanceNumber=index+1).items():
                check(getattr(ds,field,None)==expected,field,'Profile/scenario mismatch')
            for field, expected in dict(ImagePositionPatient=[0,0,index],
                ImageOrientationPatient=[1,0,0,0,1,0],PixelSpacing=[0.5,0.5]).items():
                check(list(getattr(ds,field,[]))==expected,field,'Inconsistent geometry')
            check(len(ds.PixelData)==524288,'PixelData','Incorrect byte length')
            check(ds.pixel_array.shape==(512,512),'PixelData','Decode shape mismatch')
            check(ds.SOPInstanceUID==scenario.sop_uids[index],'SOPInstanceUID','Scenario UID mismatch')
            for field in ('PatientName','PatientBirthDate','PatientSex','StudyDate','StudyTime',
                'StudyID','ReferringPhysicianName','SeriesNumber','PositionReferenceIndicator',
                'Manufacturer','ImageType','KVP','ScanOptions','ReconstructionDiameter',
                'DataCollectionDiameter','GantryDetectorTilt','TableHeight','RotationDirection',
                'ConvolutionKernel','PatientPosition','AcquisitionNumber'):
                check(field in ds,field,'Required profile attribute missing')
        except Exception as exc:
            errors.append({'standard':'DICOM','field':f'instance[{index}]','reason':str(exc)})
    return {'status':'FAILED' if errors else 'PASSED','findings':errors,
        'coverage':'Serialization/readback and synthetic CT profile; not full IOD conformance'}
