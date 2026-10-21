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

