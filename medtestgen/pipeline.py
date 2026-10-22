"""Generate, validate and package one immutable candidate dataset in RAM."""
from datetime import datetime
from io import BytesIO
import json
import pydicom

from .export import build_zip
from .generators.dicom_ct import generate_ct
from .generators.fhir_bundle import generate_fhir
from .generators.hl7_order import generate_hl7
from .models import GenerateRequest, make_scenario
from .validation.consistency import validate_consistency
from .validation.dciodvfy import validate_instances
from .validation.dicom_readback import validate_ct
from .validation.fhir import validate_fhir
from .validation.hl7 import validate_hl7


def _iso(value):
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _external_status(results):
    statuses = {item["status"] for item in results}
    return next(status for status in ("FAILED", "NOT VERIFIED", "WARNING", "PASSED") if status in statuses)


def _dicom_preview(payloads):
    preview = []
    for payload in payloads:
        ds = pydicom.dcmread(BytesIO(payload), stop_before_pixels=True)
        preview.append({
            "instance_number": int(ds.InstanceNumber),
            "sop_instance_uid": str(ds.SOPInstanceUID),
            "sop_class_uid": str(ds.SOPClassUID),
            "study_instance_uid": str(ds.StudyInstanceUID),
            "series_instance_uid": str(ds.SeriesInstanceUID),
            "frame_of_reference_uid": str(ds.FrameOfReferenceUID),
            "modality": str(ds.Modality),
            "rows": int(ds.Rows),
            "columns": int(ds.Columns),
            "pixel_spacing": [float(value) for value in ds.PixelSpacing],
            "slice_thickness": float(ds.SliceThickness),
            "image_position_patient": [float(value) for value in ds.ImagePositionPatient],
        })
    return preview


def _json_size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8"))


def build_dataset(request: GenerateRequest, dataset_id: str, created_at: datetime, expires_at: datetime):
    scenario = make_scenario(request)
    # The store timestamps govern retention; generated clinical timestamps share the same creation instant.
    scenario = scenario.copy(update={"created_at": created_at})
    dicom = generate_ct(scenario)
    hl7 = generate_hl7(scenario)
    fhir = generate_fhir(scenario)
    artifacts = {f"dicom/CT_{index:03d}.dcm": payload for index, payload in enumerate(dicom, 1)}
    artifacts["hl7/ORM_O01.hl7"] = hl7
    artifacts["fhir/bundle.json"] = fhir

    mandatory = {
        "dicom_readback": validate_ct(dicom, scenario),
        "hl7": validate_hl7(hl7),
        "fhir": validate_fhir(fhir),
        "consistency": validate_consistency(dicom, hl7, fhir),
    }
    external = validate_instances(dicom)
    for uid, result in zip(scenario.sop_uids, external):
        result["sop_instance_uid"] = uid
    external_status = _external_status(external)
    confirmed = any(item.get("confirmed_conformance_failure") for item in external)
    report = {
        "mandatory": mandatory,
        "external_status": external_status,
        "external_instances": external,
        "confirmed_conformance_failure": confirmed,
        "independent_ct_iod_check_completed": external_status in {"PASSED", "WARNING", "FAILED"},
        "conformance_claim": (
            "Independent dciodvfy check completed; this is not proof of absolute DICOM compatibility."
            if external_status in {"PASSED", "WARNING"} and not confirmed
            else "Full DICOM CT IOD conformance has not been independently verified."
        ),
    }
    previews = {
        "dicom": _dicom_preview(dicom),
        "hl7": hl7.decode("utf-8").replace("\r", "\n").rstrip(),
        "fhir": json.loads(fhir.decode("utf-8")),
    }
    record = {
        "dataset_id": dataset_id,
        "created_at": _iso(created_at),
        "expires_at": _iso(expires_at),
        "expected_instances": request.slices,
        "identifiers": {
            "patient_id": request.mrn,
            "accession_number": request.accession,
            "study_instance_uid": scenario.study_uid,
            "series_instance_uid": scenario.series_uid,
            "frame_of_reference_uid": scenario.frame_uid,
            "sop_instance_uids": list(scenario.sop_uids),
        },
        "artifacts": artifacts,
        "previews": previews,
        "report": report,
        "external_status": external_status,
        "external_instances": external,
        "confirmed_conformance_failure": confirmed,
        "zip_bytes": None,
        "state": "candidate",
        "size_bytes": 0,
    }
    record["zip_bytes"] = build_zip(record)
    record["size_bytes"] = (
        sum(len(value) for value in artifacts.values())
        + (len(record["zip_bytes"]) if record["zip_bytes"] else 0)
        + _json_size(previews) + _json_size(report) + _json_size(record["identifiers"])
    )
    return record
