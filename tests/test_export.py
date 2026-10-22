from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from io import BytesIO
import json
import zipfile

from medtestgen.export import build_zip, eligible
from medtestgen.models import GenerateRequest
from medtestgen.pipeline import build_dataset


def record():
    now = datetime.now(timezone.utc)
    return build_dataset(GenerateRequest(slices=1), "dataset-test", now, now + timedelta(minutes=30))


def test_zip_manifest_hashes_and_integrity():
    item = record()
    assert eligible(item)
    with zipfile.ZipFile(BytesIO(item["zip_bytes"])) as archive:
        assert archive.testzip() is None
        manifest = json.loads(archive.read("manifest.json"))
        for entry in manifest["files"]:
            payload = archive.read(entry["path"])
            assert entry["size"] == len(payload)
            assert entry["sha256"] == sha256(payload).hexdigest()
        assert "manifest.json" not in {entry["path"] for entry in manifest["files"]}
        assert manifest["validation"] == item["report"]


def test_every_mandatory_gate_blocks_export():
    for name in ("dicom_readback", "hl7", "fhir", "consistency"):
        for status in ("FAILED", "WARNING", "NOT VERIFIED"):
            item = record()
            item["report"]["mandatory"][name]["status"] = status
            assert not eligible(item)
            assert build_zip({**item, "zip_bytes": None}) is None


def test_external_policy_and_confirmed_failure_precedence():
    for status, allowed in (("PASSED", True), ("WARNING", True), ("NOT VERIFIED", True), ("FAILED", False)):
        item = record()
        item["report"]["external_status"] = status
        item["report"]["external_instances"][0]["status"] = status
        item["report"]["external_instances"][0]["confirmed_conformance_failure"] = status == "FAILED"
        item["confirmed_conformance_failure"] = status == "FAILED"
        assert eligible(item) is allowed
    item = record()
    item["report"]["external_status"] = "NOT VERIFIED"
    item["report"]["external_instances"][0]["status"] = "NOT VERIFIED"
    item["report"]["external_instances"][0]["confirmed_conformance_failure"] = True
    assert not eligible(item)


def test_incomplete_or_inconsistent_files_block_export():
    mutations = []
    item = record(); del item["artifacts"]["fhir/bundle.json"]; mutations.append(item)
    item = record(); item["artifacts"]["extra.txt"] = b"unexpected"; mutations.append(item)
    item = record(); item["expected_instances"] = 2; mutations.append(item)
    item = record(); item["report"]["external_instances"] = []; mutations.append(item)
    item = record(); item["zip_bytes"] = None; mutations.append(item)
    assert all(not eligible(item) for item in mutations)
