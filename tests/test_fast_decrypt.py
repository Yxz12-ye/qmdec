"""Native integration test: python -m unittest discover -s tests -v."""

from pathlib import Path
import random
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def check_native_library(directory: Path) -> None:
    from qmdec import fast_decrypt
    from qmdec.map_cipher import MapCipher
    from qmdec.rc4 import RC4Cipher

    cache = directory / fast_decrypt._SO_CACHE.name
    attempts = []
    run = subprocess.run

    def record_compile(*args, **kwargs):
        try:
            return run(*args, **kwargs)
        except subprocess.CalledProcessError as error:
            attempts.append(error.stderr.decode(errors="replace"))
            raise
        except FileNotFoundError as error:
            attempts.append(str(error))
            raise

    with patch.object(fast_decrypt, "_SO_CACHE", cache), patch.object(
        fast_decrypt.subprocess, "run", side_effect=record_compile
    ):
        assert not cache.exists(), "Test must start without a cached native library"
        assert fast_decrypt._build_lib() == cache, "Native compilation failed:\n" + "\n".join(attempts)
        assert cache.is_file() and cache.stat().st_size > 0
        print(f"Built: {cache.name} ({cache.stat().st_size} bytes)", flush=True)

        # A second build must use the cache without invoking a compiler.
        with patch.object(fast_decrypt.subprocess, "run", side_effect=AssertionError("Cache was rebuilt")):
            assert fast_decrypt._build_lib() == cache

        lib = fast_decrypt._load_lib()
        assert lib is not None, "ctypes could not load the compiled native library"
        assert fast_decrypt._load_lib() is lib
        assert lib.qmc2_decrypt is not None

        rng = random.Random(20261012)
        cases = 0
        for key_length in (0, 1, 256, 300, 301, 512):
            key = rng.randbytes(key_length)
            cipher = RC4Cipher(key) if key_length > 300 else MapCipher(key)
            for offset in (0, 127, 128, 5119, 5120, 32767, 32768):
                original = rng.randbytes(11000)
                expected = bytearray(original)
                cipher.decrypt(expected, offset)
                actual = bytearray(original)
                assert fast_decrypt.decrypt_c(key, actual, offset), "Native decrypt fell back"
                assert actual == expected, f"C/Python mismatch: key_length={key_length}, offset={offset}"
                assert fast_decrypt.decrypt_c(key, actual, offset)
                assert actual == original, "Decrypting twice should restore the input"
                assert fast_decrypt.decrypt_c(key, bytearray(), offset)
                cases += 1
        print(f"Loaded and used native library: {cases} C/Python comparisons passed", flush=True)


class FastDecryptIntegrationTest(unittest.TestCase):
    def test_build_load_and_decrypt(self):
        # The child exits before cleanup, releasing the DLL handle on Windows.
        directory = ROOT / "tests" / f".native-test-{uuid.uuid4().hex}"
        directory.mkdir()
        try:
            result = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--native-worker", str(directory)],
                capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            print(result.stdout, end="")
        finally:
            shutil.rmtree(directory)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--native-worker":
        check_native_library(Path(sys.argv[2]))
    else:
        unittest.main()
