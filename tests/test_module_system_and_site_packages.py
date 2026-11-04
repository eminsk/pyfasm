"""
Tests for whole-project multi-module resolution, topological module initialization,
and pure-Python package discovery from virtual environments.
"""
import subprocess
import tempfile
from pathlib import Path
import pytest
from pyfasm.compiler import PyFasmCompiler
from pyfasm.ast_parser import AstAnalyzer


def test_topological_module_init_order(tmp_path: Path):
    """
    Verifies that when module A imports B, and B imports C:
    Top-level code in C executes first, then B, and then A's main() executes
    with all global structures and computed values correctly initialized.
    """
    proj_dir = tmp_path / "multi_mod_proj"
    proj_dir.mkdir()

    # Module C: leaf dependency
    file_c = proj_dir / "mod_c.py"
    file_c.write_text(
        "INIT_STEP_C = 10\n"
        "C_LIST = [1, 2, 3, 4, 5]\n"
        "def get_c_sum():\n"
        "    s = 0\n"
        "    for x in C_LIST:\n"
        "        s = s + x\n"
        "    return s + INIT_STEP_C\n",
        encoding="utf-8"
    )

    # Module B: intermediate dependency
    file_b = proj_dir / "mod_b.py"
    file_b.write_text(
        "import mod_c\n"
        "B_BASE = mod_c.get_c_sum()\n"
        "B_FACTOR = 2\n"
        "def compute_b():\n"
        "    return B_BASE * B_FACTOR\n",
        encoding="utf-8"
    )

    # Module A: entry point
    file_a = proj_dir / "main.py"
    file_a.write_text(
        "import mod_b\n"
        "def main():\n"
        "    res = mod_b.compute_b()\n"
        "    print(f'COMPUTED: {res}')\n"
        "    return 0\n",
        encoding="utf-8"
    )

    compiler = PyFasmCompiler()
    out_exe = proj_dir / "app.exe"
    success, bin_path, log = compiler.compile_file(str(file_a), output_binary=str(out_exe))
    assert success, f"Compilation failed: {log}"
    assert Path(bin_path).exists()

    # Execute binary and verify execution output
    proc = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0
    # C_LIST sum = 15; + INIT_STEP_C (10) = 25; * B_FACTOR (2) = 50
    assert "COMPUTED: 50" in proc.stdout


def test_site_packages_pure_python_discovery(tmp_path: Path):
    """
    Verifies that AstAnalyzer correctly discovers and resolves pure-Python packages
    from project's .venv/Lib/site-packages, while ignoring binary extension packages.
    """
    proj_dir = tmp_path / "app_with_venv"
    proj_dir.mkdir()

    # Create mock .venv/Lib/site-packages
    site_packages = proj_dir / ".venv" / "Lib" / "site-packages"
    site_packages.mkdir(parents=True)

    # Pure-python package: simple_math
    pkg_math = site_packages / "simple_math"
    pkg_math.mkdir()
    (pkg_math / "__init__.py").write_text(
        "def add_five(x):\n"
        "    return x + 5\n",
        encoding="utf-8"
    )

    # Binary package: fake_numpy (with a fake .pyd)
    pkg_bin = site_packages / "fake_numpy"
    pkg_bin.mkdir()
    (pkg_bin / "__init__.py").write_text("import _core\n", encoding="utf-8")
    (pkg_bin / "_core.pyd").write_bytes(b"MZ\x00\x00fake_binary")

    # Main application script
    main_py = proj_dir / "main.py"
    main_py.write_text(
        "import simple_math\n"
        "def main():\n"
        "    val = simple_math.add_five(37)\n"
        "    print(f'RESULT: {val}')\n"
        "    return 0\n",
        encoding="utf-8"
    )

    analyzer = AstAnalyzer(project_root=proj_dir)
    parsed = analyzer.parse_file(main_py, project_root=proj_dir)

    # Pure-Python package should be resolved and function registered
    assert "simple_math_add_five" in parsed.functions or "add_five" in parsed.functions

    # Now compile and execute
    compiler = PyFasmCompiler()
    out_exe = proj_dir / "run_app.exe"
    success, bin_path, log = compiler.compile_file(str(main_py), output_binary=str(out_exe))
    assert success, f"Compilation failed: {log}"

    proc = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0
    assert "RESULT: 42" in proc.stdout


def test_cross_module_attribute_access_and_mutation(tmp_path: Path):
    """
    Verifies that a module's global state can be accessed and updated via
    module.attr syntax (e.g. config.SETTINGS, config.COUNTER = ...).
    """
    proj_dir = tmp_path / "mod_attr_proj"
    proj_dir.mkdir()

    # Module: config.py
    cfg_file = proj_dir / "config.py"
    cfg_file.write_text(
        "TIMEOUT = 30\n"
        "RETRIES = 3\n"
        "def get_total_wait():\n"
        "    return TIMEOUT * RETRIES\n",
        encoding="utf-8"
    )

    # Main script: main.py
    main_file = proj_dir / "main.py"
    main_file.write_text(
        "import config\n"
        "def main():\n"
        "    orig = config.TIMEOUT\n"
        "    total1 = config.get_total_wait()\n"
        "    config.TIMEOUT = 10\n"
        "    total2 = config.get_total_wait()\n"
        "    print(f'ORIG: {orig}, T1: {total1}, T2: {total2}')\n"
        "    return 0\n",
        encoding="utf-8"
    )

    compiler = PyFasmCompiler()
    out_exe = proj_dir / "test_app.exe"
    success, bin_path, log = compiler.compile_file(str(main_file), output_binary=str(out_exe))
    assert success, f"Compilation failed: {log}"

    proc = subprocess.run([str(bin_path)], capture_output=True, text=True, timeout=5)
    assert proc.returncode == 0
    assert "ORIG: 30, T1: 90, T2: 30" in proc.stdout

