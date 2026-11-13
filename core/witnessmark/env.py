"""What a run ran on (master blueprint sections 9.2 and 9.5).

Hosts are described by OS, CPU model, core count and memory only: no host
names, no user names, no paths.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from . import __version__

ZERO_COMMIT = "0" * 40


def _run(args: list[str], timeout: float = 15.0) -> str | None:
    try:
        completed = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip()


def git(repo_root: Path, *args: str) -> str | None:
    return _run(["git", "-C", str(repo_root), *args])


def harness_info(repo_root: Path) -> dict:
    """The harness commit, and whether the tree differs from it.

    Evidence written by the run itself does not count as a change.
    """
    commit = git(repo_root, "rev-parse", "HEAD") or ZERO_COMMIT
    status = git(repo_root, "status", "--porcelain", "--untracked-files=all", "--", ".", ":(exclude)evidence")
    dirty = True if status is None else bool(status)
    return {"version": __version__, "commit": commit, "dirty": dirty}


def docker(*args: str, timeout: float = 15.0) -> str | None:
    return _run(["docker", *args], timeout=timeout)


def docker_image(container: str) -> tuple[str | None, str | None]:
    """The image reference a container runs, and the content digest that pins it."""
    found = docker("inspect", "--format", "{{.Config.Image}}|{{.Image}}", container)
    if not found or "|" not in found:
        return None, None
    reference, image_id = found.split("|", 1)
    if "@sha256:" in reference:
        return reference, reference.split("@", 1)[1]
    listed = docker("image", "inspect", "--format", "{{json .RepoDigests}}", image_id)
    try:
        entries = json.loads(listed) if listed else []
    except ValueError:
        entries = []
    digests = [entry.split("@", 1)[1] for entry in entries or [] if "@" in entry]
    return reference, (digests[0] if digests else None)


def cpu_model() -> str:
    if sys.platform == "win32":
        try:
            import winreg

            path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            pass
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except OSError:
            pass
    elif sys.platform == "darwin":
        brand = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
        if brand:
            return brand
    return platform.processor() or platform.machine() or "unknown"


def total_memory_bytes() -> int:
    if sys.platform == "win32":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.ullTotalPhys)
        return 0
    if sys.platform == "darwin":
        size = _run(["sysctl", "-n", "hw.memsize"])
        return int(size) if size and size.isdigit() else 0
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (ValueError, OSError, AttributeError):
        return 0


def host_info() -> dict:
    info: dict = {
        "os": platform.platform(),
        "cpu": cpu_model(),
        "cores": os.cpu_count() or 0,
        "memory_gb": round(total_memory_bytes() / 2**30, 1),
        "python": platform.python_version(),
        "clock_offsets_ms": {},
    }
    server = docker("version", "--format", "{{.Server.Version}}")
    if server:
        info["docker"] = server
    limits = docker("info", "--format", "{{.NCPU}}|{{.MemTotal}}")
    if limits and "|" in limits:
        cpus, memory = limits.split("|", 1)
        if cpus.isdigit() and memory.isdigit():
            info["vm_cpus"] = int(cpus)
            info["vm_memory_gb"] = round(int(memory) / 2**30, 1)
    return info
