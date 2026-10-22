"""In-memory linked-standard and validation diagnostic."""
import argparse
import json
import tracemalloc
from medtestgen.models import GenerateRequest, make_scenario
from medtestgen.generators.dicom_ct import generate_ct
from medtestgen.generators.hl7_order import generate_hl7
from medtestgen.generators.fhir_bundle import generate_fhir
from medtestgen.validation.dicom_readback import validate_ct
from medtestgen.validation.hl7 import validate_hl7
from medtestgen.validation.fhir import validate_fhir
from medtestgen.validation.consistency import validate_consistency
from medtestgen.validation.dciodvfy import validate_instances
from medtestgen.validation.windows_temp import cleanup_abandoned

def generate_demo(count=5):
    scenario=make_scenario(GenerateRequest(slices=count))
    dicom=generate_ct(scenario)
    hl7=generate_hl7(scenario)
    fhir=generate_fhir(scenario)
    mandatory={'dicom_readback':validate_ct(dicom,scenario),
        'hl7':validate_hl7(hl7),'fhir':validate_fhir(fhir),
        'consistency':validate_consistency(dicom,hl7,fhir)}
    external=validate_instances(dicom)
    for uid,result in zip(scenario.sop_uids,external):
        result['sop_instance_uid']=uid
    statuses={r['status'] for r in external}
    aggregate=next(s for s in ('FAILED','NOT VERIFIED','WARNING','PASSED') if s in statuses)
    report={'synthetic_only':True,'instance_count':len(dicom),
        'patient_id':scenario.request.mrn,'accession':scenario.request.accession,
        'study_uid':scenario.study_uid,'series_uid':scenario.series_uid,
        'artifact_bytes':sum(map(len,dicom))+len(hl7)+len(fhir),
        'mandatory':mandatory,'external_status':aggregate,'external_instances':external,
        'limitations':['This CLI diagnostic does not exercise the browser or ZIP API; use the web workflow for export.',
            'Independent validator success is not universal DICOM compatibility.']}
    return report,hl7,fhir

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slices',type=int,default=5,choices=range(1,11))
    parser.add_argument('--show-output',action='store_true')
    args=parser.parse_args()
    issues=cleanup_abandoned()
    tracemalloc.start()
    report,hl7,fhir=generate_demo(args.slices)
    _,peak=tracemalloc.get_traced_memory(); tracemalloc.stop()
    report['tracked_allocation_peak_bytes']=peak
    report['cleanup_limitations']=issues
    print(json.dumps(report,indent=2))
    if args.show_output:
        print('\nHL7 ORM^O01:\n'+hl7.decode('utf-8').replace('\r','\n'))
        print('\nFHIR R4 Bundle:\n'+json.dumps(json.loads(fhir),indent=2,ensure_ascii=False))
    return 0 if all(c['status']=='PASSED' for c in report['mandatory'].values()) and report['external_status']!='FAILED' else 1

if __name__=='__main__': raise SystemExit(main())
