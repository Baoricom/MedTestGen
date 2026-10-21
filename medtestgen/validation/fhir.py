"""R4 model parsing plus explicit local profile checks, not a full FHIR engine."""
import importlib.metadata
import json
import re
from uuid import UUID

COVERAGE = {
    "fhir_release": "4.0.1",
    "models": "fhir.resources==6.1.0",
    "checks": ["R4 model structure", "local required fields and enums",
               "internal reference types", "identifier systems", "DICOM UID forms",
               "CT modality and SOP class", "series and instance counts and numbering"],
    "limitations": [
        "Not a full terminology, implementation-guide, or FHIRPath conformance engine.",
        "Cross-standard equality is checked separately against serialized DICOM and HL7."],
}
BASE = "https://medtestgen.example"
DCM = "http://dicom.nema.org/resources/ontology/DCM"
UID_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*))+")

def _uid(value):
    return isinstance(value, str) and len(value) <= 64 and bool(UID_PATTERN.fullmatch(value))

def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object property")
        result[key] = value
    return result

def validate_fhir(payload: bytes) -> dict:
    findings = []
    def fail(path, reason):
        findings.append({"path": path, "reason": reason})
    def check(condition, path, reason):
        if not condition:
            fail(path, reason)
    result = {"status": "NOT VERIFIED", "findings": findings, "coverage": COVERAGE}
    try:
        import fhir.resources
        from fhir.resources.bundle import Bundle
        from pydantic import ValidationError
        if (importlib.metadata.version("fhir.resources") != "6.1.0"
                or fhir.resources.__fhir_version__ != "4.0.1"):
            fail("$", "Qualified FHIR R4 4.0.1 model package unavailable")
            return result
    except ImportError:
        fail("$", "FHIR R4 validation model dependency unavailable")
        return result
    try:
        data = json.loads(payload.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeError, ValueError, TypeError, AttributeError):
        fail("$", "Expected unique-key JSON encoded in UTF-8")
        result["status"] = "FAILED"
        return result
    try:
        Bundle.parse_obj(data)
    except ValidationError as exc:
        for error in exc.errors():
            fail(".".join(str(part) for part in error["loc"]), error["msg"])
        result["status"] = "FAILED"
        return result
    except (ValueError, TypeError):
        fail("$", "Could not parse FHIR Bundle structure")
        result["status"] = "FAILED"
        return result
    # This generated profile uses no primitive-array extension placeholders.
    # Reject JSON nulls explicitly instead of silently dropping malformed content.
    def reject_nulls(value, path="$"):
        if value is None:
            fail(path, "JSON null is not permitted in this generated profile")
        elif isinstance(value, dict):
            for key, item in value.items():
                reject_nulls(item, path + "." + key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                reject_nulls(item, f"{path}[{index}]")
    reject_nulls(data)
    if findings:
        result["status"] = "FAILED"
        return result
    # The pinned Pydantic generation may coerce numbers into FHIR strings.
    # Inspect original JSON primitives rather than trusting coerced model values.
    string_fields = {"resourceType", "id", "system", "value", "family", "text",
                     "birthDate", "gender", "reference", "status", "intent",
                     "display", "authoredOn", "started", "description", "uid",
                     "fullUrl", "code", "type"}
    def check_primitives(value, path="$"):
        if isinstance(value, dict):
            for key, item in value.items():
                location = path + "." + key
                if key in string_fields and not isinstance(item, (dict, list, str)):
                    fail(location, "Expected a JSON string, without scalar coercion")
                if key == "given" and isinstance(item, list):
                    check(all(isinstance(v, str) for v in item), location,
                          "Given name components must be strings")
                check_primitives(item, location)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                check_primitives(item, f"{path}[{index}]")
    check_primitives(data)
    if findings:
        result["status"] = "FAILED"
        return result
    check(data.get("resourceType") == "Bundle", "resourceType", "Expected Bundle")
    check(data.get("type") == "collection", "type", "Expected collection")
    entries = data.get("entry") or []
    check(len(entries) == 3, "entry", "Expected exactly three entries")
    resources, urls = {}, set()
    for index, entry in enumerate(entries):
        path = f"entry[{index}]"
        resource = entry.get("resource") or {}
        kind = resource.get("resourceType")
        if kind not in ("Patient", "ServiceRequest", "ImagingStudy") or kind in resources:
            fail(path + ".resource", "Expected one each of Patient, ServiceRequest, ImagingStudy")
            continue
        resources[kind] = resource
        ident = resource.get("id", "")
        try:
            valid_id = str(UUID(ident)) == ident
        except (ValueError, TypeError, AttributeError):
            valid_id = False
        check(valid_id, path + ".resource.id", "Expected canonical UUID resource ID")
        full_url = entry.get("fullUrl")
        check(full_url == "urn:uuid:" + ident, path + ".fullUrl",
              "fullUrl must be urn:uuid:<resource id>")
        check(full_url not in urls, path + ".fullUrl", "Duplicate fullUrl")
        urls.add(full_url)
        check("request" not in entry, path + ".request", "Collection has no transaction requests")
    if set(resources) != {"Patient", "ServiceRequest", "ImagingStudy"}:
        fail("entry", "Missing required resource types")
        result["status"] = "FAILED"
        return result
    patient, order, study = (resources[k] for k in ("Patient", "ServiceRequest", "ImagingStudy"))
    patient_url = "urn:uuid:" + patient.get("id", "")
    order_url = "urn:uuid:" + order.get("id", "")
    for label, resource in (("ServiceRequest", order), ("ImagingStudy", study)):
        check((resource.get("subject") or {}).get("reference") == patient_url,
              label + ".subject.reference", "Must resolve to the bundled Patient")
    check(study.get("basedOn") == [{"reference": order_url}], "ImagingStudy.basedOn",
          "Must resolve only to the bundled ServiceRequest")
    check(patient.get("gender") in ("male", "female", "other", "unknown"),
          "Patient.gender", "Expected generated-profile gender")
    check(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", patient.get("birthDate", ""))),
          "Patient.birthDate", "Full birth date required")
    names = patient.get("name") or []
    check(len(names) == 1 and bool(names[0].get("family")), "Patient.name",
          "Exactly one structured family name required")
    if len(names) == 1:
        given = names[0].get("given") or []
        check(len(given) <= 1, "Patient.name[0].given", "At most one given component")
        check(bool(names[0].get("text")), "Patient.name[0].text", "Display name required")

    def identifier(resource, label, system):
        selected = [item for item in resource.get("identifier", []) if item.get("system") == system]
        check(len(selected) == 1 and bool(selected[0].get("value")), label + ".identifier",
              "Exactly one nonempty identifier required for system " + system)
        return selected[0].get("value", "") if len(selected) == 1 else ""

    identifier(patient, "Patient", BASE + "/identifier/mrn")
    accession = identifier(order, "ServiceRequest", BASE + "/identifier/accession")
    filler = identifier(order, "ServiceRequest", BASE + "/identifier/filler-order")
    identifier(order, "ServiceRequest", BASE + "/identifier/placer-order")
    study_accession = identifier(study, "ImagingStudy", BASE + "/identifier/accession")
    check(accession == filler == study_accession, "ImagingStudy.identifier",
          "Accession and local filler identifiers must agree")
    check(order.get("status") == "active", "ServiceRequest.status", "Expected active")
    check(order.get("intent") == "order", "ServiceRequest.intent", "Expected order")
    check(study.get("status") == "available", "ImagingStudy.status", "Expected available")
    coding = (order.get("code") or {}).get("coding") or []
    description = (order.get("code") or {}).get("text")
    check(len(coding) == 1 and coding[0].get("system") == BASE + "/codes/procedure"
          and coding[0].get("code") == "CT_SYNTHETIC", "ServiceRequest.code.coding",
          "Expected local CT_SYNTHETIC procedure coding")
    check(bool(description) and study.get("description") == description
          and len(coding) == 1 and coding[0].get("display") == description,
          "ServiceRequest.code", "Procedure text/display and study description must agree")
    check(bool(order.get("authoredOn")) and order.get("authoredOn") == study.get("started"),
          "ServiceRequest.authoredOn", "Matching scenario timestamps required")
    check(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|\+00:00)",
                           order.get("authoredOn", ""))),
          "ServiceRequest.authoredOn", "Full UTC timestamp required")
    study_uid = identifier(study, "ImagingStudy", "urn:dicom:uid")
    check(study_uid.startswith("urn:oid:") and _uid(study_uid[8:]),
          "ImagingStudy.identifier", "Study UID requires urn:oid:<valid DICOM UID>")
    expected_modality = {"system": DCM, "code": "CT"}
    check(study.get("modality") == [expected_modality], "ImagingStudy.modality",
          "Expected DICOM CT modality")
    series_list = study.get("series") or []
    check(type(study.get("numberOfSeries")) is int and study["numberOfSeries"] == 1
          and len(series_list) == 1, "ImagingStudy.series", "Exactly one series required")
    if len(series_list) == 1:
        series = series_list[0]
        check(_uid(series.get("uid")), "ImagingStudy.series[0].uid", "Expected bare DICOM UID")
        check(series.get("modality") == expected_modality, "ImagingStudy.series[0].modality",
              "Expected DICOM CT modality")
        check(type(series.get("number")) is int and series["number"] == 1,
              "ImagingStudy.series[0].number", "Expected series number 1")
        instances = series.get("instance") or []
        count = len(instances)
        check(1 <= count <= 10 and type(study.get("numberOfInstances")) is int
              and type(series.get("numberOfInstances")) is int
              and study["numberOfInstances"] == series["numberOfInstances"] == count,
              "ImagingStudy.numberOfInstances", "Counts must match actual 1–10 instances")
        uids = set()
        for index, instance in enumerate(instances):
            path = f"ImagingStudy.series[0].instance[{index}]"
            uid = instance.get("uid")
            check(_uid(uid), path + ".uid", "Expected bare DICOM UID")
            check(uid not in uids and uid not in (series.get("uid"), study_uid[8:]),
                  path + ".uid", "Instance UID must be distinct")
            uids.add(uid)
            check(type(instance.get("number")) is int and instance["number"] == index + 1,
                  path + ".number", "Expected contiguous instance numbers in order")
            check(instance.get("sopClass") == {
                "system": "urn:ietf:rfc:3986", "code": "urn:oid:1.2.840.10008.5.1.4.1.1.2"},
                path + ".sopClass", "Expected CT Image Storage SOP class URI")
        check(series.get("uid") != study_uid[8:], "ImagingStudy.series[0].uid",
              "Study and series UIDs must differ")
    result["status"] = "FAILED" if findings else "PASSED"
    return result
