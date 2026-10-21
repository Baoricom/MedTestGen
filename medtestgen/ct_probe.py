"""Runnable CT risk proof. Generated DICOM stays in RAM."""
import argparse
import json
from medtestgen.models import GenerateRequest, make_scenario
from medtestgen.generators.dicom_ct import generate_ct
from medtestgen.validation.dicom_readback import validate_ct
from medtestgen.validation.dciodvfy import validate_instances

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--slices',type=int,default=5)
    args=parser.parse_args()
    scenario=make_scenario(GenerateRequest(slices=args.slices))
    instances=generate_ct(scenario)
    external=validate_instances(instances)
    for uid, result in zip(scenario.sop_uids,external):
        result['sop_instance_uid']=uid
    print(json.dumps({'synthetic_only':True,'study_uid':scenario.study_uid,
        'series_uid':scenario.series_uid,'instance_count':len(instances),
        'readback':validate_ct(instances,scenario),'external':external},indent=2))

if __name__=='__main__': main()