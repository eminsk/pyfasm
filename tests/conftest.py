import sys
import shutil
import subprocess
import pytest

_orig_run = subprocess.run


def _patched_run(args, *pargs, **kwargs):
    if sys.platform != "win32" and isinstance(args, (list, tuple)) and args:
        cmd = str(args[0])
        if cmd.endswith(".exe") or ".exe" in cmd:
            wine = shutil.which("wine")
            if wine:
                return _orig_run([wine] + list(args), *pargs, **kwargs)
            pytest.skip("Running Windows PE (.exe) binary on non-Windows platform requires Wine")
    return _orig_run(args, *pargs, **kwargs)


subprocess.run = _patched_run
