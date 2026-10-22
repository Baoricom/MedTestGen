# MedTestGen

One Patient. Three Standards. Consistent Test Data.

Synthetic Data — Not for Clinical Use.

The approved P0 implementation is complete. The browser application generates linked CT DICOM, HL7 ORM^O01 and FHIR R4 data, reports actual validation outcomes, retains results in RAM and exports only eligible datasets. Main generated payloads remain in RAM. Only the approved validator method A uses one temporary seekable DICOM file at a time. No real medical data is used.

## Windows setup

Qualified target: Windows 10 build 19045, Python 3.10 x64. Windows 11 is not yet tested.

```powershell
git clone https://github.com/Baoricom/MedTestGen.git
Set-Location .\MedTestGen
python -c "import struct, sys; assert sys.version_info[:2] == (3, 10) and struct.calcsize('P') == 8, 'Python 3.10 x64 is required'; print(sys.version)"
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -r requirements-validator.txt
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -c "from medtestgen.validation.dciodvfy import locate_validator; print(locate_validator())"
& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\python.exe -m uvicorn medtestgen.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

The validator-location command must print the bundled `dciodvfy.exe` path, package version `20260927`, and the qualified binary digest. A failure here means the independent CT IOD check will be reported as `NOT VERIFIED`; reinstall with `requirements-validator.txt` and confirm that 64-bit Python 3.10 is active.

Open http://127.0.0.1:8000. Keep this PowerShell window open while using the application. Do not enable Uvicorn reload for a demonstration because a restart clears RAM datasets. Application logging does not retain payloads. The ZIP is assembled in RAM and sent to the browser; the server does not save it in the project.

## Validation limitations

Readback is not full DICOM conformance. dciodvfy findings apply only to the tool and profile checked, not absolute compatibility with every device. Unknown diagnostic grammar is NOT VERIFIED, never silently PASSED. Confirmed conformance failures cannot be downgraded. There is no method B fallback.

Delete-on-close requires the qualified Python/Windows/binary combination. Power loss, OS crash, secure erasure and unrelated antivirus/file-lock behavior are not guaranteed. Parent/child lifecycle and cleanup tests document the scenarios actually exercised. See `devpost/spec.md` and `devpost/build-evidence.md` for the approved scope and verified behavior.
## Stage 2 checkpoint: one patient, three standards

```powershell
& .\.venv\Scripts\python.exe -m medtestgen.demo --slices 5 --show-output
```

This creates five CT instances, one ORM^O01 and one FHIR R4 collection Bundle in memory. It prints actual DICOM readback, HL7 structure, FHIR resource/profile, cross-standard consistency and per-instance dciodvfy results, followed by the HL7 message and FHIR JSON. Inspect matching MRN/accession and the DICOM/FHIR study/series/instance UIDs. It does not save dataset files or produce a ZIP.

`--slices 10` exercises the maximum approved study size. Reported tracked allocation peak is a tracemalloc observation, not total process RSS or proof of future store capacity. Retention/admission limits are implemented and tested in slice 3.

For exact environment reproduction use `python -m pip install -r requirements-lock.txt` inside the project venv. The lock includes the qualified optional validator and test tools.

HL7 validation uses hl7apy's original field/group definitions with the order-detail choice narrowed to OBR. hl7apy 1.3.5 incorrectly validates every alternative as required; the local profile corrects this without adding unrelated order segments. Missing OBR and missing procedure remain test failures.

## Stage 3 API

The backend retains datasets in RAM for 30 minutes, enforces atomic replacement and rechecks validation before every ZIP response. API tests use FastAPI's in-process client; generated ZIP files are not written to the project.

The application must run as one Uvicorn worker. Multiple workers would create separate RAM stores and are outside the approved MVP architecture.

## Browser workflow

The form starts with synthetic values and a five-slice CT Head study. Generate Dataset creates and validates all three standards. The result tabs show a phantom preview and DICOM identifiers, the serialized ORM message, and formatted FHIR JSON. Download ZIP is enabled only when the backend export predicate permits it. The active `dataset_id` is retained in `sessionStorage`; refreshing the same tab restores an unexpired result.

If mandatory validation or confirmed CT IOD conformance fails, diagnostics remain visible and ZIP stays blocked. An unavailable external validator is shown as NOT VERIFIED with an explicit limitation; it is not reported as PASSED.

## Planning and verification evidence

The Devpost Learn planning documents are in `devpost/scope.md`, `devpost/prd.md`, `devpost/spec.md`, `devpost/checklist.md`, and `devpost/app-map.html`. Actual build checks are recorded in `devpost/build-evidence.md`. The private learner profile and planning-only validator research are intentionally excluded from the public repository.

## License

MedTestGen is available under the MIT License. See `LICENSE`.
