from medtestgen.validation.hl7 import validate_order_tree
from hl7apy.core import Message
from medtestgen.models import Scenario

def escape(value):
    codes={'|':'F','^':'S','~':'R','\\':'E','&':'T'}
    return ''.join('\\'+codes[c]+'\\' if c in codes else c for c in str(value))

def generate_hl7(scenario: Scenario) -> bytes:
    r=scenario.request
    message=Message('ORM_O01',version='2.5.1')
    msh=message.msh
    msh.msh_3='MEDTESTGEN'; msh.msh_4='SYNTHETIC'
    msh.msh_5='TEST_RECEIVER'; msh.msh_6='TEST_FACILITY'
    timestamp=scenario.created_at.strftime('%Y%m%d%H%M%S+0000')
    msh.msh_7=timestamp; msh.msh_9='ORM^O01^ORM_O01'
    msh.msh_10=scenario.message_id; msh.msh_11='T'; msh.msh_12='2.5.1'
    msh.msh_18='UNICODE UTF-8'
    patient=message.add_group('ORM_O01_PATIENT')
    pid=patient.add_segment('PID')
    pid.pid_1='1'; pid.pid_3=f'{escape(r.mrn)}^^^MEDTESTGEN^MR'
    pid.pid_5='^'.join(escape(part) for part in r.patient_name.split('^'))
    pid.pid_7=r.birth_date.strftime('%Y%m%d'); pid.pid_8=r.sex
    visit=patient.add_group('ORM_O01_PATIENT_VISIT').add_segment('PV1')
    visit.pv1_1='1'; visit.pv1_2='O'
    order=message.add_group('ORM_O01_ORDER')
    orc=order.add_segment('ORC')
    orc.orc_1='NW'; orc.orc_2=f'{scenario.order_id}^MEDTESTGEN'
    orc.orc_3=f'{escape(r.accession)}^MEDTESTGEN'; orc.orc_9=timestamp
    detail=order.add_group('ORM_O01_ORDER_DETAIL')
    obr=detail.add_group('ORM_O01_OBRRQDRQ1RXOODSODT_SUPPGRP').add_segment('OBR')
    obr.obr_1='1'; obr.obr_2=orc.orc_2.value; obr.obr_3=orc.orc_3.value
    obr.obr_4=f'CT_SYNTHETIC^{escape(r.description)}^99MEDTESTGEN'
    obr.obr_18=escape(r.accession)
    validate_order_tree(message)
    return (message.to_er7()+'\r').encode('utf-8')
