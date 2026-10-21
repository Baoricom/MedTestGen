"""Serialize the approved local FHIR R4 collection profile to UTF-8 bytes."""
import json
from medtestgen.models import Scenario

BASE = "https://medtestgen.example"
MRN = BASE + "/identifier/mrn"
ACCESSION = BASE + "/identifier/accession"
PLACER = BASE + "/identifier/placer-order"
FILLER = BASE + "/identifier/filler-order"
PROCEDURE = BASE + "/codes/procedure"
DCM = "http://dicom.nema.org/resources/ontology/DCM"
CT_CLASS = "urn:oid:1.2.840.10008.5.1.4.1.1.2"

def generate_fhir(scenario: Scenario) -> bytes:
    request = scenario.request
    family, _, given = request.patient_name.partition("^")
    patient_url = "urn:uuid:" + scenario.patient_uuid
    order_url = "urn:uuid:" + scenario.order_uuid
    timestamp = scenario.created_at.isoformat(timespec="seconds").replace("+00:00", "Z")
    name = {"text": request.patient_name, "family": family}
    if given:
        name["given"] = [given]
    patient = {
        "resourceType": "Patient", "id": scenario.patient_uuid,
        "identifier": [{"system": MRN, "value": request.mrn}],
        "name": [name], "birthDate": request.birth_date.isoformat(),
        "gender": {"M": "male", "F": "female", "O": "other", "U": "unknown"}[request.sex],
    }
    order = {
        "resourceType": "ServiceRequest", "id": scenario.order_uuid,
        "identifier": [
            {"system": ACCESSION, "value": request.accession},
            {"system": PLACER, "value": scenario.order_id},
            {"system": FILLER, "value": request.accession}],
        "status": "active", "intent": "order",
        "subject": {"reference": patient_url},
        "code": {"coding": [{"system": PROCEDURE, "code": "CT_SYNTHETIC",
                              "display": request.description}], "text": request.description},
        "authoredOn": timestamp,
    }
    study = {
        "resourceType": "ImagingStudy", "id": scenario.study_uuid,
        "identifier": [{"system": "urn:dicom:uid", "value": "urn:oid:" + scenario.study_uid},
                       {"system": ACCESSION, "value": request.accession}],
        "status": "available", "subject": {"reference": patient_url},
        "basedOn": [{"reference": order_url}], "started": timestamp,
        "description": request.description, "numberOfSeries": 1,
        "numberOfInstances": request.slices,
        "modality": [{"system": DCM, "code": "CT"}],
        "series": [{
            "uid": scenario.series_uid, "number": 1,
            "modality": {"system": DCM, "code": "CT"},
            "numberOfInstances": request.slices,
            "instance": [{"uid": uid, "number": index,
                          "sopClass": {"system": "urn:ietf:rfc:3986", "code": CT_CLASS}}
                         for index, uid in enumerate(scenario.sop_uids, 1)],
        }],
    }
    bundle = {"resourceType": "Bundle", "type": "collection", "entry": [
        {"fullUrl": "urn:uuid:" + resource["id"], "resource": resource}
        for resource in (patient, order, study)]}
    return json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
