# MedTestGen

One Patient. Three Standards. Consistent Test Data.

Synthetic Data — Not for Clinical Use.

Implementation is in progress. Slices 1 and 2 are implemented: the runnable entry points generate CT alone or linked DICOM/HL7/FHIR in RAM. The web application, retained dataset API and ZIP export are not implemented yet. Main generated payloads remain in RAM. Only the approved validator method A uses a temporary seekable DICOM file. No real medical data is used.

## Windows setup

Qualified target: Windows 10 build 19045, Python 3.10 x64. Windows 11 is not yet tested.

```powershell
Set-Location 'C:\Projects\MedTestGen'
py -3.10 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -r requirements-validator.txt
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\python.exe -m pytest
& .\.venv\Scripts\python.exe -m medtestgen.ct_probe --slices 5
```

The probe prints synthetic identifiers and actual validation findings explicitly requested for inspection. Application logging must not retain payloads. No DICOM file or ZIP is written to the project.

## Validation limitations

Readback is not full DICOM conformance. dciodvfy findings apply only to the tool and profile checked, not absolute compatibility with every device. Unknown diagnostic grammar is NOT VERIFIED, never silently PASSED. Confirmed conformance failures cannot be downgraded. There is no method B fallback.

Delete-on-close requires the qualified Python/Windows/binary combination. Power loss, OS crash, secure erasure and unrelated antivirus/file-lock behavior are not guaranteed. Parent/child lifecycle and cleanup tests document the scenarios actually exercised. See devpost/spec.md and the historical validator PoC reports for the approved scope.
## Stage 2 checkpoint: one patient, three standards

```powershell
& .\.venv\Scripts\python.exe -m medtestgen.demo --slices 5 --show-output
```

This creates five CT instances, one ORM^O01 and one FHIR R4 collection Bundle in memory. It prints actual DICOM readback, HL7 structure, FHIR resource/profile, cross-standard consistency and per-instance dciodvfy results, followed by the HL7 message and FHIR JSON. Inspect matching MRN/accession and the DICOM/FHIR study/series/instance UIDs. It does not save dataset files or produce a ZIP.

`--slices 10` exercises the maximum approved study size. Reported tracked allocation peak is a tracemalloc observation, not total process RSS or proof of future store capacity. Retention/admission limits are implemented and tested in slice 3.

For exact environment reproduction use `python -m pip install -r requirements-lock.txt` inside the project venv. The lock includes the qualified optional validator and test tools.

HL7 validation uses hl7apy's original field/group definitions with the order-detail choice narrowed to OBR. hl7apy 1.3.5 incorrectly validates every alternative as required; the local profile corrects this without adding unrelated order segments. Missing OBR and missing procedure remain test failures.

## Stage 3 API

The backend now retains datasets in RAM for 30 minutes, enforces atomic replacement and rechecks validation before every ZIP response. The final browser entry point is added in Stage 4. API tests use FastAPI's in-process client; generated ZIP files are not written to the project.

The application must run as one Uvicorn worker. Multiple workers would create separate RAM stores and are outside the approved MVP architecture.
