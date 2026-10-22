from io import BytesIO
import json
import zipfile

from fastapi.testclient import TestClient
from medtestgen.main import create_app


def new_session(client):
    response = client.post("/api/session")
    assert response.status_code == 201
    return response.json()


def test_page_contains_approved_generator_and_accessibility_hooks():
    with TestClient(create_app()) as client:
        page = client.get("/")
        assert page.status_code == 200
        for text in (
            "One Patient. Three Standards.", "Consistent Test Data.",
            "Synthetic Data — Not for Clinical Use", "Generate Dataset",
            "Randomize Patient", "CT Image Storage", "Download ZIP",
        ):
            assert text in page.text
        for identity in ("patient-name", "mrn", "birth-date", "sex", "description", "accession", "slices"):
            assert f'id="{identity}"' in page.text
        assert 'role="tablist"' in page.text and page.text.count('role="tabpanel"') == 3
        assert "default-src 'self'" in page.headers["content-security-policy"]
        assert page.headers["cache-control"] == "no-store"


def test_frontend_uses_session_storage_and_safe_text_rendering():
    with TestClient(create_app()) as client:
        script = client.get("/static/app.js").text
        assert "sessionStorage" in script
        assert "localStorage" not in script
        assert ".innerHTML" not in script
        assert "textContent" in script
        assert 'expected_revision:state.revision' in script
        assert 'Back to Previous Valid Result' in client.get("/").text


def test_complete_five_slice_http_journey_and_refresh_recovery():
    with TestClient(create_app()) as client:
        session = new_session(client)
        headers = {"X-MedTestGen-Session": session["token"]}
        payload = {
            **session["defaults"], "slices": 5, "expected_revision": 0,
            "request_id": "complete_ui_journey",
        }
        generated = client.post("/api/datasets", headers=headers, json=payload)
        assert generated.status_code == 201, generated.text
        body = generated.json()
        dataset = body["dataset"]
        assert dataset["eligible"] and dataset["expected_instances"] == 5
        assert len(dataset["previews"]["dicom"]) == 5
        assert dataset["previews"]["hl7"].startswith("MSH|")
        assert [entry["resource"]["resourceType"] for entry in dataset["previews"]["fhir"]["entry"]] == [
            "Patient", "ServiceRequest", "ImagingStudy"
        ]
        assert all(result["status"] == "PASSED" for result in dataset["report"]["mandatory"].values())
        assert dataset["report"]["external_status"] == "PASSED"
        restored = client.get("/api/session", headers=headers).json()
        assert restored["active_id"] == dataset["dataset_id"] and restored["revision"] == 1
        preview = client.get(f'/api/datasets/{restored["active_id"]}', headers=headers)
        assert preview.status_code == 200 and preview.json()["eligible"]
        archive_response = client.get(f'/api/datasets/{restored["active_id"]}/zip', headers=headers)
        with zipfile.ZipFile(BytesIO(archive_response.content)) as archive:
            assert archive.testzip() is None
            assert len([name for name in archive.namelist() if name.endswith(".dcm")]) == 5
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["dataset_id"] == dataset["dataset_id"]


def test_api_returns_actionable_invalid_input_without_traceback():
    with TestClient(create_app()) as client:
        session = new_session(client)
        response = client.post("/api/datasets", headers={"X-MedTestGen-Session": session["token"]}, json={
            **session["defaults"], "slices": 25, "expected_revision": 0,
            "request_id": "invalid_ui_request",
        })
        assert response.status_code == 422
        data = response.json()
        assert data["code"] == "INVALID_INPUT" and data["fields"]
        assert "Traceback" not in response.text
