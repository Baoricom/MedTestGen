"""Pinned dciodvfy diagnostic adapter. All results and diagnostics remain in RAM."""
import hashlib
import importlib.metadata
import os
from pathlib import Path
import re
import sys
import threading
from .windows_temp import OwnedFile, run_supervised

VERSION = "20260927"
DIGEST = "7f42d1d165d4f8d4e436d863501a6c8c50987b671d7f5c2fe83c662a227cd14b"
_LOCK = threading.Lock()

def locate_validator():
    if os.name != "nt" or sys.version_info[:2] != (3, 10):
        raise OSError("Validator method A requires qualified Windows/Python 3.10")
    import dicom3tools
    version = importlib.metadata.version("dicom3tools")
    executable = Path(dicom3tools.bin_dir()) / "dciodvfy.exe"
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    if version != VERSION or digest != DIGEST:
        raise OSError("Validator package or binary is not the qualified version")
    return str(executable), version, digest

def classify(result):
    findings, unknown = [], False
    identified = False
    for line in (result.get("stdout", "") + "\n" + result.get("stderr", "")).splitlines():
        line = line.strip()
        if line == "CTImage":
            identified = True
            continue
        if not line:
            continue
        match = re.match(r"^(Error|Warning) - (.+)$", line)
        tags = re.findall(r"\([0-9A-Fa-f]{4},[0-9A-Fa-f]{4}\)", line)
        # Only recorded grammar establishing a base IOD constraint is confirmed.
        confirmed = bool(match and match[1] == "Error" and tags
                         and "Module=<" in line and "profile" not in line.lower()
                         and ("Missing attribute for Type " in line
                              or "Attribute present when condition unsatisfied " in line))
        warning = bool(match and match[1] == "Warning" and tags and (
            "Missing attribute or value that would be needed to build DICOMDIR" in line
            or "is only permitted to be empty when actually unknown;" in line))
        if not confirmed and not warning:
            unknown = True
        findings.append(dict(text=line, tags=tags,
                             severity=match[1].upper() if match else "UNKNOWN",
                             confirmed_conformance_failure=confirmed))
    failure = any(f["confirmed_conformance_failure"] for f in findings)
    incomplete = (not identified or unknown or result.get("technical_error") or result.get("timeout")
                  or result.get("overflow") or not result.get("cleanup_ok")
                  or not result.get("child_reaped") or result.get("exit_code") != 0)
    result["findings"] = findings
    result["confirmed_conformance_failure"] = failure
    result["status"] = ("FAILED" if failure else "NOT VERIFIED" if incomplete else
                        "WARNING" if findings else "PASSED")
    if unknown:
        result["parser_limitation"] = "Unrecognized diagnostic; conformance is not verified"
    return result

def validate_instances(instances: list[bytes]) -> list[dict]:
    results = []
    with _LOCK:
        try:
            executable, version, digest = locate_validator()
            unavailable = None
        except (ImportError, OSError, importlib.metadata.PackageNotFoundError) as exc:
            executable, version, digest = None, None, None
            unavailable = str(exc)
        for index, payload in enumerate(instances):
            result = dict(instance_index=index, invocation_attempted=False, stdout="", stderr="",
                          exit_code=None, timeout=False, overflow=False, cleanup_ok=False,
                          child_reaped=False, parser_version=VERSION,
                          tool_version=version, binary_sha256=digest, technical_error=unavailable)
            owned = None
            if executable:
                try:
                    owned = OwnedFile(payload)
                    with owned:
                        result["invocation_attempted"] = True
                        result.update(run_supervised([executable, "-new", str(owned.path)]))
                        for stream in ("stdout", "stderr"):
                            result[stream] = result[stream].replace(str(owned.path), "<temporary DICOM>")
                except Exception as exc:
                    result["technical_error"] = type(exc).__name__ + ": validator invocation failed"
                finally:
                    if owned is not None:
                        result["cleanup_ok"] = owned.cleanup_ok
            results.append(classify(result))
    return results
