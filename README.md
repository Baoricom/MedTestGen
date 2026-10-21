# MedTestGen

One Patient. Three Standards. Consistent Test Data.

Synthetic Data — Not for Clinical Use.

Implementation is in progress. At slice 1 the runnable entry point is a CT diagnostic probe, not the web application. Main generated payloads remain in RAM. Only the approved validator method A uses a temporary seekable DICOM file. No real medical data is used.

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