"""Windows method A and kill-on-close child supervision; no alternate transport."""
import ctypes
from ctypes import wintypes
import os
from itertools import islice
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import threading
import time
import uuid

ROOT = Path(tempfile.gettempdir()) / "medtestgen-validator"
MARKER = b"MedTestGen validator ownership v1\n"

def _plain(path):
    return path.exists() and not path.is_symlink() and not (
        path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)

def cleanup_abandoned():
    """Bounded recovery. Never delete unknown contents or traverse reparse points."""
    issues = []
    if os.name != "nt" or not ROOT.exists():
        return issues
    if not _plain(ROOT):
        return ["Temporary root is not a plain owned directory"]
    import msvcrt
    for run in islice(ROOT.iterdir(), 100):
        if not re.fullmatch(r"run-[0-9a-f]{32}", run.name):
            continue
        lock = None
        try:
            if not _plain(run) or not run.is_dir():
                raise OSError("Unsafe run directory")
            entries = list(run.iterdir())
            if any(not _plain(p) for p in entries):
                raise OSError("Unsafe run entry")
            if any(p.name not in {"owner", "lock"} and
                   not re.fullmatch(r"instance-[a-z0-9_]{8}\.dcm", p.name)
                   for p in entries):
                raise OSError("Unknown entries; retained")
            if any(not p.is_file() or p.parent != run for p in entries):
                raise OSError("Unsafe owned file")
            if (run / "owner").read_bytes() != MARKER:
                raise OSError("Ownership mismatch")
            lock = open(run / "lock", "r+b")
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            # Lock is held through deletion of all recognized remnants.
            for entry in entries:
                if entry.name not in {"owner", "lock"}:
                    entry.unlink()
            lock.close()
            lock = None
            (run / "lock").unlink()
            (run / "owner").unlink()
            run.rmdir()
        except OSError:
            issues.append("Owned temporary run remains active, locked, or unsafe")
        finally:
            if lock is not None:
                lock.close()
    return issues

class OwnedFile:
    def __init__(self, payload):
        self.payload = payload
        self.file = self.lock = self.directory = None
        self.cleanup_ok = False

    def __enter__(self):
        if os.name != "nt":
            raise OSError("Windows method A is not qualified on this platform")
        import msvcrt
        ROOT.mkdir(exist_ok=True)
        if not _plain(ROOT):
            raise OSError("Unsafe temporary root")
        self.directory = ROOT / ("run-" + uuid.uuid4().hex)
        self.directory.mkdir()
        try:
            (self.directory / "owner").write_bytes(MARKER)
            self.lock = open(self.directory / "lock", "w+b")
            self.lock.write(b"1")
            self.lock.flush()
            self.lock.seek(0)
            msvcrt.locking(self.lock.fileno(), msvcrt.LK_NBLCK, 1)
            self.file = tempfile.NamedTemporaryFile(
                mode="w+b", suffix=".dcm", prefix="instance-", delete=True,
                dir=self.directory)
            self.path = Path(self.file.name)
            self.file.write(self.payload)
            self.file.flush()
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        try:
            if self.file:
                self.file.close()
                if self.path.exists():
                    raise OSError("Delete-on-close file remains")
            if self.lock:
                self.lock.close()
            if self.directory:
                for name in ("lock", "owner"):
                    (self.directory / name).unlink(missing_ok=True)
                self.directory.rmdir()
            self.cleanup_ok = True
        except OSError:
            self.cleanup_ok = False
        finally:
            if self.lock:
                self.lock.close()

class Job:
    """Assign a suspended child before allowing any validator code to run."""
    def __init__(self):
        if os.name != "nt":
            raise OSError("Windows Job Objects unavailable")
        class BASIC(ctypes.Structure):
            _fields_ = [("ProcessTime", ctypes.c_int64), ("JobTime", ctypes.c_int64),
                        ("Flags", wintypes.DWORD), ("Min", ctypes.c_size_t),
                        ("Max", ctypes.c_size_t), ("Count", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("Priority", wintypes.DWORD),
                        ("Scheduling", wintypes.DWORD)]
        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in
                        ("ReadOps", "WriteOps", "OtherOps", "ReadBytes", "WriteBytes", "OtherBytes")]
        class EXT(ctypes.Structure):
            _fields_ = [("Basic", BASIC), ("IO", IO), ("ProcessMemory", ctypes.c_size_t),
                        ("JobMemory", ctypes.c_size_t), ("PeakProcess", ctypes.c_size_t),
                        ("PeakJob", ctypes.c_size_t)]
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.api.CreateJobObjectW.restype = wintypes.HANDLE
        self.api.SetInformationJobObject.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.api.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.api.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        info = EXT()
        info.Basic.Flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.api.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            self.close()
            raise OSError("Cannot configure validator Job Object")

    def assign_resume(self, process):
        if not self.api.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise OSError("Cannot assign validator to Job Object")
        nt = ctypes.WinDLL("ntdll")
        nt.NtResumeProcess.argtypes = [wintypes.HANDLE]
        nt.NtResumeProcess.restype = ctypes.c_long
        if nt.NtResumeProcess(int(process._handle)) != 0:
            raise OSError("Cannot resume supervised validator")

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None

def run_supervised(command, timeout=10.0, capture_limit=256 * 1024):
    """Drain concurrently; never retain more than capture_limit bytes per stream."""
    result = dict(stdout="", stderr="", exit_code=None, timeout=False,
                  overflow=False, technical_error=None, child_reaped=False)
    job, process = Job(), None
    buffers = [bytearray(), bytearray()]
    overflow = threading.Event()
    readers = []
    def drain(stream, buffer):
        while True:
            chunk = stream.read(4096)
            if not chunk:
                return
            remaining = capture_limit - len(buffer)
            buffer.extend(chunk[:max(0, remaining)])
            if len(chunk) > remaining:
                overflow.set()
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False, creationflags=0x08000000 | 0x00000004)
        job.assign_resume(process)
        for stream, buffer in zip((process.stdout, process.stderr), buffers):
            thread = threading.Thread(target=drain, args=(stream, buffer), daemon=True)
            thread.start()
            readers.append(thread)
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            if overflow.is_set() or time.monotonic() >= deadline:
                result["timeout"] = not overflow.is_set()
                break
            time.sleep(0.01)
    except Exception as exc:
        result["technical_error"] = type(exc).__name__ + ": validator supervision failed"
    finally:
        # Close job before releasing the data handle, including on cancellation.
        job.close()
        if process is not None:
            try:
                process.wait(timeout=5)
                result["child_reaped"] = True
                result["exit_code"] = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=5)
                    result["child_reaped"] = True
                except subprocess.TimeoutExpired:
                    result["technical_error"] = "Validator child could not be reaped"
            for thread in readers:
                thread.join(timeout=5)
            for stream in (process.stdout, process.stderr):
                stream.close()
        result["overflow"] = overflow.is_set()
        result["stdout"], result["stderr"] = [
            bytes(b).decode("utf-8", "replace") for b in buffers]
    return result
