import os
import sys
import shutil
import subprocess
import pytest

os.environ.setdefault("WINEDEBUG", "-all")

_orig_run = subprocess.run


def _patched_run(args, *pargs, **kwargs):
    """Run compiled Windows PE binaries through Wine on non-Windows hosts.

    On hosts with Wine (e.g. Linux CI with Wine installed), binaries run under Wine.
    On non-Windows hosts without Wine (e.g. Apple macOS runners), the Windows PE execution
    is safely skipped unless PYFASM_REQUIRE_WINE=1 is set.
    """
    if sys.platform != "win32" and isinstance(args, (list, tuple)) and args:
        cmd = str(args[0])
        if ".exe" in cmd.lower():
            wine = shutil.which("wine") or shutil.which("wine64")
            if not wine:
                if os.environ.get("PYFASM_REQUIRE_WINE") == "1":
                    raise RuntimeError(
                        "Wine is required to execute the compiled Windows PE binary "
                        f"{cmd!r} on {sys.platform}. Install it (Debian/Ubuntu: "
                        "'sudo apt-get install wine wine64', macOS: "
                        "'brew install --cask wine-stable')."
                    )
                pytest.skip(
                    f"Running Windows PE binary {cmd!r} on {sys.platform} requires Wine"
                )
            return _orig_run([wine] + list(args), *pargs, **kwargs)
    return _orig_run(args, *pargs, **kwargs)


subprocess.run = _patched_run
