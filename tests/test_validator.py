"""Real binary tests are required qualification, never counted when skipped."""
import ctypes
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from medtestgen.validation import dciodvfy as adapter
from medtestgen.validation import windows_temp as transport

def positive_fixture():
    import pydicom
    from pydicom.dataset import FileDataset, FileMetaDataset
    from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = CTImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    meta.ImplementationClassUID = pydicom.uid.PYDICOM_IMPLEMENTATION_UID
    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
    values = dict(
        SOPClassUID=CTImageStorage, SOPInstanceUID=meta.MediaStorageSOPInstanceUID,
        PatientName="SYNTHETIC^PHANTOM", PatientID="TEST-001",
        PatientBirthDate="19700101", PatientSex="O",
        StudyInstanceUID=generate_uid(), SeriesInstanceUID=generate_uid(),
        FrameOfReferenceUID=generate_uid(), StudyDate="20261021", StudyTime="120000",
        ReferringPhysicianName="", StudyID="1", AccessionNumber="TEST-001",
        Modality="CT", SeriesNumber=1, PatientPosition="HFS",
        PositionReferenceIndicator="", Manufacturer="SYNTHETIC",
        InstanceNumber=1, ImageType=["DERIVED", "SECONDARY", "AXIAL"],
        AcquisitionNumber=1, ImagePositionPatient=[0, 0, 0],
        ImageOrientationPatient=[1, 0, 0, 0, 1, 0], PixelSpacing=[0.5, 0.5],
        SliceThickness=1, Rows=16, Columns=16, SamplesPerPixel=1,
        PhotometricInterpretation="MONOCHROME2", BitsAllocated=16, BitsStored=16,
        HighBit=15, PixelRepresentation=0, RescaleIntercept=-1024, RescaleSlope=1,
        RescaleType="HU", KVP="", ScanOptions="", DataCollectionDiameter="",
        ReconstructionDiameter="", GantryDetectorTilt="", TableHeight="",
        RotationDirection="", ConvolutionKernel="", LossyImageCompression="00",
        PatientOrientation="", BurnedInAnnotation="NO", BodyPartExamined="HEAD",
        DerivationDescription="Synthetic test phantom; not for clinical use",
    )
    for key, value in values.items():
        setattr(ds, key, value)
    ds.PixelData = b"\0" * (16 * 16 * 2)
    return ds

def serialize(ds):
    import pydicom
    stream = io.BytesIO()
    pydicom.dcmwrite(stream, ds, enforce_file_format=True)
    return stream.getvalue()

ERROR = "Error - </PixelSpacing(0028,0030)> - Missing attribute for Type 1 Required - Module=<ImagePlane>"
WARNING = "Warning - </PatientID(0010,0020)> - Missing attribute or value that would be needed to build DICOMDIR"

class ParserTests(unittest.TestCase):
    def result(self, text, **updates):
        result = dict(stdout="", stderr=text, exit_code=0, cleanup_ok=True,
                      child_reaped=True, timeout=False, overflow=False)
        result.update(updates)
        result["stderr"] = "CTImage\n" + result["stderr"]
        return adapter.classify(result)

    def test_recorded_diagnostics(self):
        self.assertEqual(self.result("CTImage\n")["status"], "PASSED")
        self.assertEqual(self.result(WARNING)["status"], "WARNING")
        for updates in ({}, {"cleanup_ok": False}, {"timeout": True}, {"overflow": True}):
            result = self.result(ERROR, **updates)
            self.assertEqual(result["status"], "FAILED")
            self.assertTrue(result["confirmed_conformance_failure"])

    def test_uncertain_diagnostics_never_pass(self):
        for text, updates in [
            ("future output", {}), ("Error - Cannot open file", {}),
            ("", {"exit_code": 1}), ("CTImage", {"overflow": True}),
            ("CTImage", {"cleanup_ok": False}), ("CTImage", {"timeout": True}),
            (ERROR + " profile vendor", {})]:
            self.assertEqual(self.result(text, **updates)["status"], "NOT VERIFIED")

    def test_empty_output_is_not_verified(self):
        result = adapter.classify(dict(stdout="", stderr="", exit_code=0,
                                       cleanup_ok=True, child_reaped=True))
        self.assertEqual(result["status"], "NOT VERIFIED")

    def test_missing_tool_has_result_for_every_instance(self):
        with patch.object(adapter, "locate_validator", side_effect=OSError("missing tool")):
            results = adapter.validate_instances([b"a", b"b", b"c"])
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r["status"] == "NOT VERIFIED" for r in results))

@unittest.skipUnless(os.name == "nt", "Windows qualification requires Windows")
class WindowsTests(unittest.TestCase):
    def test_success_timeout_overflow_and_cleanup(self):
        for code, timeout, limit, expected in [
            ("print('ok')", 2, 1024, None),
            ("import time; time.sleep(30)", .05, 1024, "timeout"),
            ("print('x'*1000000)", 2, 1024, "overflow")]:
            owned = transport.OwnedFile(b"synthetic test")
            with owned:
                result = transport.run_supervised([sys.executable, "-c", code],
                                                  timeout=timeout, capture_limit=limit)
            self.assertTrue(owned.cleanup_ok)
            self.assertFalse(owned.path.exists())
            self.assertTrue(result["child_reaped"])
            if expected:
                self.assertTrue(result[expected])
            self.assertLessEqual(len(result["stdout"]), limit)

    def test_exception_while_child_active_is_reaped(self):
        original = transport.Job.assign_resume
        pids = []
        def resume_raise(job, process):
            original(job, process)
            pids.append(process.pid)
            raise RuntimeError("injected after resume")
        owned = transport.OwnedFile(b"synthetic test")
        with owned, patch.object(transport.Job, "assign_resume", resume_raise):
            result = transport.run_supervised(
                [sys.executable, "-c", "import time; time.sleep(30)"])
        self.assertTrue(pids)
        self.assertTrue(result["child_reaped"])
        self.assertTrue(owned.cleanup_ok)

    def test_cleanup_refuses_unknown_and_active(self):
        owned = transport.OwnedFile(b"synthetic test")
        with owned:
            transport.cleanup_abandoned()
            self.assertTrue(owned.path.exists())
            unknown = owned.directory / "unrelated.txt"
            unknown.write_text("retain")
            try:
                transport.cleanup_abandoned()
                self.assertTrue(unknown.exists())
                self.assertTrue(owned.path.exists())
            finally:
                unknown.unlink()
        self.assertTrue(owned.cleanup_ok)

    def test_adapter_timeout_is_not_verified(self):
        outcome = dict(stdout="", stderr="", exit_code=1, timeout=True,
                       overflow=False, child_reaped=True, technical_error=None)
        with patch.object(adapter, "run_supervised", return_value=outcome):
            result = adapter.validate_instances([b"synthetic test"])[0]
        self.assertEqual(result["status"], "NOT VERIFIED")
        self.assertTrue(result["cleanup_ok"])

    def test_reparse_attribute_is_refused(self):
        from unittest.mock import Mock
        from types import SimpleNamespace
        import stat
        candidate = Mock()
        candidate.exists.return_value = True
        candidate.is_symlink.return_value = False
        candidate.lstat.return_value = SimpleNamespace(
            st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT)
        self.assertFalse(transport._plain(candidate))
        owned = transport.OwnedFile(b"synthetic test")
        with owned:
            original = transport._plain
            with patch.object(transport, "_plain",
                              side_effect=lambda p: False if p == owned.directory else original(p)):
                transport.cleanup_abandoned()
                self.assertTrue(owned.path.exists())
        self.assertTrue(owned.cleanup_ok)

    def test_abandoned_known_file_recovery(self):
        # Only synthetic bytes; ownership marker and released lock emulate crash debris.
        import uuid
        transport.ROOT.mkdir(exist_ok=True)
        directory = transport.ROOT / ("run-" + uuid.uuid4().hex)
        directory.mkdir()
        try:
            (directory / "owner").write_bytes(transport.MARKER)
            (directory / "lock").write_bytes(b"1")
            (directory / "instance-abcdefgh.dcm").write_bytes(b"synthetic test")
            transport.cleanup_abandoned()
            self.assertFalse(directory.exists())
        finally:
            if directory.exists():
                for name in ("instance-abcdefgh.dcm", "lock", "owner"):
                    (directory / name).unlink(missing_ok=True)
                directory.rmdir()

    def test_unqualified_runtime_does_not_create_file(self):
        with patch.object(adapter.sys, "version_info", (3, 12, 0)):
            results = adapter.validate_instances([b"synthetic test"])
        self.assertEqual(results[0]["status"], "NOT VERIFIED")
        self.assertFalse(results[0]["invocation_attempted"])

    def test_owner_death_with_live_reader(self):
        child_code = (
            "import os,sys,time; "
            "fd=os.open(sys.argv[1],os.O_RDONLY|os.O_BINARY|os.O_TEMPORARY); "
            "print('reader-ready',flush=True); time.sleep(30)"
        )
        owner_code = (
            "import json,subprocess,sys,time; "
            "from medtestgen.validation.windows_temp import OwnedFile,Job; "
            "f=OwnedFile(b'synthetic test'); f.__enter__(); j=Job(); "
            "p=subprocess.Popen([sys.executable,'-c'," + repr(child_code) + ",str(f.path)],"
            "stdout=subprocess.PIPE,text=True,creationflags=0x08000004); "
            "j.assign_resume(p); ready=p.stdout.readline().strip(); "
            "print(json.dumps([p.pid,str(f.path),ready]),flush=True); time.sleep(30)"
        )
        owner = subprocess.Popen([sys.executable, "-c", owner_code],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, creationflags=0x08000000)
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        api.OpenProcess.restype = ctypes.c_void_p
        api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        api.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = None
        try:
            # Bounded readiness: collect a line in a daemon thread.
            import queue, threading
            lines = queue.Queue()
            threading.Thread(target=lambda: lines.put(owner.stdout.readline()),
                             daemon=True).start()
            pid, filename, ready = json.loads(lines.get(timeout=10))
            self.assertEqual(ready, "reader-ready")
            handle = api.OpenProcess(0x100000, False, pid)
            self.assertTrue(handle)
            self.assertEqual(api.WaitForSingleObject(handle, 0), 258)
            owner.kill()
            owner.wait(timeout=5)
            self.assertEqual(api.WaitForSingleObject(handle, 5000), 0)
            deadline = time.monotonic() + 5
            while Path(filename).exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertFalse(Path(filename).exists())
            transport.cleanup_abandoned()
            self.assertFalse(Path(filename).parent.exists())
        finally:
            if owner.poll() is None:
                owner.kill()
                owner.wait(timeout=5)
            owner.stdout.close()
            owner.stderr.close()
            if handle:
                api.CloseHandle(handle)

@unittest.skipUnless(os.name == "nt", "Real validator requires qualified Windows")
class RealValidatorTests(unittest.TestCase):
    def test_generated_studies_one_through_ten(self):
        from medtestgen.models import GenerateRequest, make_scenario
        from medtestgen.generators.dicom_ct import generate_ct
        for count in range(1, 11):
            results = adapter.validate_instances(
                generate_ct(make_scenario(GenerateRequest(slices=count))))
            self.assertEqual(len(results), count)
            self.assertTrue(all(r["status"] == "PASSED" for r in results), results)
            self.assertTrue(all(r["cleanup_ok"] for r in results))

    def test_all_instances_positive_warning_and_failures(self):
        # Intentionally fail rather than skip if the pinned tool is unavailable.
        adapter.locate_validator()
        positive = positive_fixture()
        missing = positive_fixture()
        del missing.PixelSpacing
        warning = positive_fixture()
        warning.PatientID = ""
        conditional = positive_fixture()
        conditional.Laterality = ""
        results = adapter.validate_instances(
            [serialize(ds) for ds in (positive, missing, warning, conditional)])
        self.assertEqual([r["status"] for r in results],
                         ["PASSED", "FAILED", "WARNING", "FAILED"], results)
        self.assertEqual(results[-1]["exit_code"], 0)
        self.assertTrue(all(r["cleanup_ok"] and r["child_reaped"] for r in results))
        self.assertTrue(all(r["invocation_attempted"] for r in results))
        self.assertTrue(all("Temp\\" not in r["stderr"] for r in results))

if __name__ == "__main__":
    unittest.main()
