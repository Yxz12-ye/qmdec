"""C-accelerated QMC2 decrypt with pure-Python fallback."""

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

_lib = None
_CSRC = Path(__file__).parent / "csrc" / "qmc2_fast.c"
_SO_CACHE = Path(__file__).parent / "csrc" / (
    "qmc2fast.dll" if os.name == "nt" else "libqmc2fast.so"
)


def _build_lib() -> Path | None:
    if _SO_CACHE.exists():
        return _SO_CACHE
    if not _CSRC.exists():
        return None
    if os.name == "nt":
        commands = []
        if clang := shutil.which("clang"):
            commands.append([
                clang, "-O3", "-shared", "-o", str(_SO_CACHE), str(_CSRC),
                "-Wl,/EXPORT:qmc2_decrypt",
            ])
        commands.append([
            "cl", "/nologo", "/O2", "/LD", str(_CSRC), f"/Fe:{_SO_CACHE}",
            "/link", "/EXPORT:qmc2_decrypt",
        ])
    else:
        commands = [[
            "gcc", "-O3", "-shared", "-fPIC", "-lm", "-o",
            str(_SO_CACHE), str(_CSRC),
        ]]
    for command in commands:
        try:
            subprocess.run(command, check=True, capture_output=True)
            return _SO_CACHE
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return None


def _load_lib():
    global _lib
    if _lib is not None:
        return _lib
    so_path = _build_lib()
    if so_path is None:
        return None
    try:
        _lib = ctypes.CDLL(str(so_path))
        _lib.qmc2_decrypt.argtypes = [
            ctypes.c_char_p, ctypes.c_int,
            ctypes.c_char_p, ctypes.c_int, ctypes.c_int,
        ]
        _lib.qmc2_decrypt.restype = None
        return _lib
    except OSError:
        return None


def decrypt_c(key: bytes, data: bytearray, offset: int = 0) -> bool:
    lib = _load_lib()
    if lib is None:
        return False
    buf = (ctypes.c_char * len(data)).from_buffer(data)
    lib.qmc2_decrypt(key, len(key), buf, len(data), offset)
    return True
