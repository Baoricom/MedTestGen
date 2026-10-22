"""Single backend export policy and deterministic in-memory ZIP creation."""
from hashlib import sha256
from io import BytesIO
import json
import zipfile

MANDATORY = {"dicom_readback", "hl7", "fhir", "consistency"}
EXTERNAL_ALLOWED = {"PASSED", "WARNING", "NOT VERIFIED"}


def required_paths(record):
    count = record.get("expected_instances", 0)
    return {
        *(f"dicom/CT_{index:03d}.dcm" for index in range(1, count + 1)),
        "hl7/ORM_O01.hl7",
        "fhir/bundle.json",
    }


def eligible(record, require_zip=True):
    """Re-evaluate every approved export gate; never trust a cached flag."""
    try:
        report = record["report"]
        mandatory = report["mandatory"]
        if set(mandatory) != MANDATORY:
            return False
        if any(mandatory[name].get("status") != "PASSED" for name in MANDATORY):
            return False
        expected = record["expected_instances"]
        external = report["external_instances"]
        if len(external) != expected or {item.get("instance_index") for item in external} != set(range(expected)):
            return False
        if report.get("external_status") not in EXTERNAL_ALLOWED:
            return False
        if any(item.get("status") not in EXTERNAL_ALLOWED for item in external):
            return False
        confirmed = report.get("confirmed_conformance_failure") or record.get("confirmed_conformance_failure")
        confirmed = confirmed or any(item.get("confirmed_conformance_failure") for item in external)
        confirmed = confirmed or any(
            finding.get("confirmed_conformance_failure")
            for item in external for finding in item.get("findings", [])
        )
        if confirmed:
            return False
        artifacts = record["artifacts"]
        if set(artifacts) != required_paths(record) or any(not isinstance(value, bytes) or not value for value in artifacts.values()):
            return False
        return not require_zip or isinstance(record.get("zip_bytes"), bytes) and bool(record["zip_bytes"])
    except (KeyError, TypeError, ValueError):
        return False


def build_manifest(record):
    artifacts = record["artifacts"]
    files = [
        {"path": path, "size": len(payload), "sha256": sha256(payload).hexdigest()}
        for path, payload in sorted(artifacts.items())
    ]
    report = record["report"]
    return {
        "schema_version": "1.0",
        "dataset_id": record["dataset_id"],
        "created_at": record["created_at"],
        "expires_at": record["expires_at"],
        "synthetic_data": True,
        "clinical_use": False,
        "notice": "Synthetic Data — Not for Clinical Use",
        "identifiers": record["identifiers"],
        "files": files,
        "validation": report,
        "limitations": [
            "dciodvfy results are independent evidence, not proof of universal DICOM compatibility.",
            "A NOT VERIFIED external result permits export only because every mandatory check passed.",
        ],
    }


def build_zip(record):
    if not eligible(record, require_zip=False):
        return None
    manifest = json.dumps(build_manifest(record), ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path, payload in sorted(record["artifacts"].items()):
            archive.writestr(path, payload)
        archive.writestr("manifest.json", manifest)
    payload = stream.getvalue()
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity verification failed")
        if set(archive.namelist()) != required_paths(record) | {"manifest.json"}:
            raise ValueError("ZIP membership verification failed")
    return payload
