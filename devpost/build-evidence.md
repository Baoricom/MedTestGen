# Build verification evidence

## Slice 1

Environment: Windows 10 build 19045, Python 3.10.11 x64. Pinned runtime/development/validator packages installed in project .venv; resolved versions retained in requirements-lock.txt.

- pip check: no broken requirements.
- Runtime import smoke: FastAPI, hl7apy, pydicom, NumPy and FHIR Bundle imports succeeded. FHIR version asserted as 4.0.1.
- CT tests: 19 passed, including N=1..10, UID uniqueness, pixel/geometry profile, Unicode and input errors.
- Real dciodvfy checked all 55 instances across counts 1..10; every instance passed and cleanup was verified.
- Real positive/missing PixelSpacing/warning-only/exit-zero conditional violation controls returned PASSED/FAILED/WARNING/FAILED respectively.
- Timeout, bounded output, missing tool, exception during active child execution, and abrupt owner death with a live delete-sharing reader exercised. Child termination and owned-file cleanup checked.

Readback and independent-validator results have separate coverage. This does not establish universal DICOM interoperability. Windows 11, power loss and arbitrary third-party file locks remain unverified. Export gating is not implemented until slice 3, so no ZIP-blocking API test is claimed here.
Final slice 1 regression: 33 passed (19 CT + 14 validator). Reparse refusal uses mocked file attributes; actual junction and third-party-lock qualification are not claimed.

## Slice 2

Final full regression: 84 passed in 8.19 seconds, no skips. The additional 51 tests exercise HL7/FHIR output and cross-standard consistency, including malformed resources, missing OBR/procedure, invalid versions, Unicode/escaping, identifier/UID/order mismatches, references and timestamps.

Actual integrated maximum-size run generated ten CT instances, one ORM and a Bundle containing Patient, ServiceRequest and ImagingStudy. DICOM readback, HL7 structure, FHIR R4 validation and cross-standard consistency each returned PASSED. All ten external instances returned PASSED and cleanup_ok=true.

Artifacts totaled 5,260,880 bytes for that run. tracemalloc peak was 23,268,649 bytes (~22.2 MiB), below the proposed 64 MiB generation reservation. This measurement excludes the future retained store/ZIP and is not total process RSS. Capacity enforcement and API export veto tests remain slice 3 work.

No full DICOM compatibility claim is made. No dataset payloads were saved to project storage. The terminal demo is the slice 2 review surface; the web UI remains slice 4 work.

## Slice 3

Full regression after the RAM store and API implementation: 104 passed in 15.45 seconds, no skipped tests. `pip check` reported no broken requirements. The warnings were a Starlette TestClient deprecation notice and inability to write pytest's optional cache in the restricted project environment; neither test execution nor assertions were skipped.

The tests exercise the 30-minute TTL boundary, automatic cleanup, owner-scoped 410/404 behavior, backend concurrency admission, stale revisions, rollback after validation and system errors, preservation of the previous active result without extending its TTL, one latest failed candidate, restart loss, memory reservations/releases, direct ZIP denial for every mandatory status, external FAILED and confirmed-failure precedence, allowed WARNING/NOT VERIFIED policy, exact archive membership, CRC and SHA-256 manifest integrity.

An actual ten-instance API request returned HTTP 201. DICOM readback, HL7, FHIR and consistency were PASSED; the external aggregate was PASSED. The ZIP returned HTTP 200, contained thirteen entries (ten DICOM files plus HL7, FHIR and manifest), and `ZipFile.testzip()` returned no corrupt member. The retained record accounted for 5,318,691 bytes. `tracemalloc` observed a 27,376,567-byte peak, below the 64 MiB generation reservation. This is not a whole-process RSS guarantee.

The backend re-evaluates export eligibility on each download. It never exposes a raw DICOM artifact route. Main payloads, ZIP and reports remain in RAM. The only disk-backed generated content remains the approved one-at-a-time validator file.

## Slice 4

Final automated regression: 108 passed in 16.29 seconds with no skipped tests; `pip check` found no broken requirements and `node --check medtestgen/static/app.js` succeeded. The same two non-failing environment warnings remained: Starlette TestClient deprecation and unavailable optional pytest cache writes.

The local app was started with the documented single-worker Uvicorn command and exercised through a real browser. The prefilled five-slice form generated a result showing Required Checks Passed. DICOM readback, HL7 structure, FHIR R4, cross-standard consistency and the independent CT IOD aggregate each visibly showed PASSED. The DICOM tab displayed a phantom and five distinct SOP Instance UIDs with coherent slice positions. The HL7 tab displayed MSH/PID/PV1/ORC/OBR, and the FHIR tab displayed Patient, ServiceRequest and ImagingStudy with resolved UUID references and five instances.

The browser Download ZIP action was invoked. Archive membership and integrity were independently verified in the same five-slice HTTP journey: five DICOM files, `hl7/ORM_O01.hl7`, `fhir/bundle.json`, and `manifest.json`; CRC passed and manifest dataset identity matched. Reloading the page restored the same active result through `sessionStorage`. Submitting 11 slices produced an actionable 422 field message without traceback and did not destroy the active result.

Visual inspection confirmed the light responsive layout, status labels, validation cards, tabs, phantom preview and download action at the desktop viewport. CSS breakpoints and semantic/keyboard hooks have automated checks; a physical Windows 11/mobile-device run remains unverified and does not block the approved Windows 10 MVP.
