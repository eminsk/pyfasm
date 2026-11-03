import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_context_manager_with_file_write_and_read(tmp_path: Path):
    target_data_file = (tmp_path / "sample.txt").resolve()
    target_data_str = str(target_data_file).replace("\\", "\\\\")

    source = f"""
def main() -> int:
    path = "{target_data_str}"

    # Test writing with context manager
    with open(path, "w") as f:
        f.write("Line 1 from PyFASM!\\n")
        f.write("Line 2 from native code!\\n")

    # Test reading back with context manager
    with open(path, "r") as f:
        content = f.read()
        print("Read content:")
        print(content)

    return 0
"""
    src_file = tmp_path / "with_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "with_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Line 1 from PyFASM!" in res.stdout
    assert "Line 2 from native code!" in res.stdout
    assert target_data_file.exists()
    assert "Line 1 from PyFASM!" in target_data_file.read_text(encoding="utf-8")


def test_file_append_and_direct_helpers(tmp_path: Path):
    target_data_file = (tmp_path / "append_test.txt").resolve()
    target_data_str = str(target_data_file).replace("\\", "\\\\")

    source = f"""
def main() -> int:
    path = "{target_data_str}"

    # Initial write
    with open(path, "w") as f:
        f.write("FirstPart-")

    # Append
    with open(path, "a") as f:
        f.write("AppendedPart")

    # Read back using file_read helper
    data = file_read(path)
    print("Combined file data:", data)
    return 0
"""
    src_file = tmp_path / "append_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "append_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "Combined file data: FirstPart-AppendedPart" in res.stdout
