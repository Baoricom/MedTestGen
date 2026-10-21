from io import BytesIO
import numpy as np
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian
from medtestgen.models import Scenario

def generate_ct(scenario: Scenario) -> list[bytes]:
    request = scenario.request
    y, x = np.ogrid[:512, :512]
    pixels = np.zeros((512, 512), dtype='<u2')
    pixels[(x-256)**2 + (y-256)**2 < 180**2] = 1024
    pixels[(x-210)**2 + (y-240)**2 < 30**2] = 1500
    pixels[280:320, 280:320] = 750
    result = []
    for index, uid in enumerate(scenario.sop_uids):
        meta = FileMetaDataset()
        meta.MediaStorageSOPClassUID = CTImageStorage
        meta.MediaStorageSOPInstanceUID = uid
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        meta.ImplementationClassUID = pydicom.uid.PYDICOM_IMPLEMENTATION_UID
        ds = FileDataset(None, {}, file_meta=meta, preamble=b'\0'*128)
        values = dict(SOPClassUID=CTImageStorage, SOPInstanceUID=uid,
            SpecificCharacterSet='ISO_IR 192', PatientName=request.patient_name,
            PatientID=request.mrn, IssuerOfPatientID='MEDTESTGEN',
            PatientBirthDate=request.birth_date.strftime('%Y%m%d'),
            PatientSex='' if request.sex == 'U' else request.sex,
            StudyInstanceUID=scenario.study_uid, SeriesInstanceUID=scenario.series_uid,
            FrameOfReferenceUID=scenario.frame_uid,
            StudyDate=scenario.created_at.strftime('%Y%m%d'),
            StudyTime=scenario.created_at.strftime('%H%M%S'), TimezoneOffsetFromUTC='+0000',
            ReferringPhysicianName='', StudyID='1', AccessionNumber=request.accession,
            StudyDescription=request.description, Modality='CT', SeriesNumber=1,
            BodyPartExamined='HEAD', PatientPosition='HFS', PositionReferenceIndicator='',
            Manufacturer='MEDTESTGEN', InstanceNumber=index+1,
            ImageType=['DERIVED','SECONDARY','AXIAL'], AcquisitionNumber=1,
            ImagePositionPatient=[0,0,index], ImageOrientationPatient=[1,0,0,0,1,0],
            PixelSpacing=[0.5,0.5], SliceThickness=1, Rows=512, Columns=512,
            SamplesPerPixel=1, PhotometricInterpretation='MONOCHROME2', BitsAllocated=16,
            BitsStored=16, HighBit=15, PixelRepresentation=0, RescaleIntercept=-1024,
            RescaleSlope=1, RescaleType='HU', WindowCenter=40, WindowWidth=400,
            KVP='', ScanOptions='', DataCollectionDiameter='', ReconstructionDiameter='',
            GantryDetectorTilt='', TableHeight='', RotationDirection='', ConvolutionKernel='',
            LossyImageCompression='00', PatientOrientation='', BurnedInAnnotation='NO',
            DerivationDescription='Synthetic geometric phantom; not for clinical use')
        for key, value in values.items():
            setattr(ds, key, value)
        ds.PixelData = pixels.tobytes()
        buffer = BytesIO()
        pydicom.dcmwrite(buffer, ds, enforce_file_format=True)
        result.append(buffer.getvalue())
    return result
