import os
import sys
import shutil
import subprocess

os.environ.setdefault("WINEDEBUG", "-all")

_orig_run = subprocess.run


def _patched_run(args, *pargs, **kwargs):
    """Run compiled Windows PE binaries through Wine on non-Windows hosts.

    Without Wine the binary cannot be executed, so the test fails with a clear
    message instead of passing over the check.
    """
    if sys.platform != "win32" and isinstance(args, (list, tuple)) and args:
        cmd = str(args[0])
        if ".exe" in cmd.lower():
            wine = shutil.which("wine") or shutil.which("wine64")
            if not wine:
                raise RuntimeError(
                    "Wine is required to execute the compiled Windows PE binary "
                    f"{cmd!r} on {sys.platform}. Install it (Debian/Ubuntu: "
                    "'sudo apt-get install wine wine64', macOS: "
                    "'brew install --cask wine-stable')."
                )
            return _orig_run([wine] + list(args), *pargs, **kwargs)
    return _orig_run(args, *pargs, **kwargs)


subprocess.run = _patched_run
