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
