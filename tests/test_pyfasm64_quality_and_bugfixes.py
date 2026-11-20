from __future__ import annotations
import ctypes
import re
import subprocess
import sys
from pathlib import Path
import pytest

import pyfasm
import pyfasm64
from pyfasm import runtime_linux, runtime_macos, runtime_win64
from pyfasm.ast_parser import AstAnalyzer
from pyfasm.bundler import ProjectBundler
from pyfasm.cli import main as cli_main
from pyfasm.compiler import PyFasmCompiler
from pyfasm.fasm_exporter import FasmExporter
from pyfasm.optimizer import PeepholeOptimizer, optimize_fasm_code

REPO_ROOT = Path(__file__).resolve().parents[1]


def _compile_and_run_win64(tmp_path: Path, code: str, name: str = "prog") -> subprocess.CompletedProcess:
    src = tmp_path / f"{name}.py"
    exe = tmp_path / f"{name}.exe"
    src.write_text(code, encoding="utf-8")
    compiler = PyFasmCompiler()
    ok, out_exe, log = compiler.compile_file(str(src), output_binary=str(exe), target="win64")
    assert ok, f"Compilation failed:\n{log}"
    return subprocess.run([out_exe], capture_output=True, text=True, timeout=10)


def test_pyfasm64_and_pyfasm_api_and_version_sync():
    for attr in (
        "__version__",
        "PyFasmCompiler",
        "ProjectBundler",
        "FasmExporter",
        "PeepholeOptimizer",
        "optimize_fasm_code",
        "main",
    ):
        assert hasattr(pyfasm, attr), f"pyfasm missing {attr}"
        assert hasattr(pyfasm64, attr), f"pyfasm64 missing {attr}"
        assert getattr(pyfasm, attr) is getattr(pyfasm64, attr)

    pyproject_text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m_pyproj = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.M)
    assert m_pyproj is not None
    expected_ver = m_pyproj.group(1)

    assert pyfasm.__version__ == expected_ver
    assert pyfasm64.__version__ == expected_ver

    recipe_text = (REPO_ROOT / "recipe" / "recipe.yaml").read_text(encoding="utf-8")
    m_recipe = re.search(r'^\s*version:\s*"([^"]+)"', recipe_text, re.M)
    assert m_recipe is not None and m_recipe.group(1) == expected_ver

    changelog_text = (REPO_ROOT / "debian" / "changelog").read_text(encoding="utf-8")
    m_deb = re.match(r'^python3-pyfasm64\s+\(([^)-]+)-\d+\)', changelog_text)
    assert m_deb is not None and m_deb.group(1) == expected_ver

    assert (REPO_ROOT / "src" / "pyfasm" / "py.typed").exists()
    assert (REPO_ROOT / "src" / "pyfasm64" / "py.typed").exists()


def test_readme_files_are_synchronized():
    assert (REPO_ROOT / "src" / "pyfasm" / "README.md").read_text(encoding="utf-8") == (
        REPO_ROOT / "README.md"
    ).read_text(encoding="utf-8")
    assert (REPO_ROOT / "src" / "pyfasm" / "README_RU.md").read_text(encoding="utf-8") == (
        REPO_ROOT / "README_RU.md"
    ).read_text(encoding="utf-8")


def test_python_m_cli_version_and_empty_emit_asm(tmp_path: Path):
    for mod in ("pyfasm64", "pyfasm"):
        res = subprocess.run(
            [sys.executable, "-m", mod, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert res.returncode == 0, res.stderr
        assert pyfasm64.__version__ in res.stdout

    empty_dir = tmp_path / "empty_proj"
    empty_dir.mkdir()
    old_argv = sys.argv
    try:
        sys.argv = ["pyfasm64", "emit-asm", str(empty_dir)]
        rc = cli_main()
        assert rc == 1
    finally:
        sys.argv = old_argv


def test_compile_no_asm_cross_dir_and_no_0121_hijack(tmp_path: Path):
    src_dir = tmp_path / "app_0121"
    out_dir = tmp_path / "dist_out"
    src_dir.mkdir()
    src_file = src_dir / "main.py"
    src_file.write_text(
        "def main() -> int:\n    print(42)\n    return 0\n",
        encoding="utf-8",
    )

    out_bin = out_dir / ("app.exe" if sys.platform == "win32" else "app.elf")
    target = "win64" if sys.platform == "win32" else "linux"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(
        str(src_file),
        output_binary=str(out_bin),
        target=target,
        keep_asm=False,
    )
    assert ok, f"compile_file keep_asm=False failed: {log}"
    assert Path(bin_path).exists()
    assert not (src_dir / "asm").exists()

    asm = compiler.compile_source_to_asm(src_file.read_text(encoding="utf-8"), project_dir=str(src_dir))
    assert "xlsx" not in asm.lower() and "ribbon" not in asm.lower()


def test_bundler_dir_mode_subdir_entry_and_exporter_sh(tmp_path: Path):
    bundler = ProjectBundler()
    dir_asm = bundler.generate_launcher_asm(
        entry_script=str(tmp_path / "my app" / "main.py"),
        is_gui=False,
        app_title="DirModeApp",
        target="win64",
        onefile=False,
    )
    assert isinstance(dir_asm, str)
    assert "format PE64 console 5.0" in dir_asm
    assert "\\\\" not in dir_asm

    proj = tmp_path / "nested_proj"
    sub = proj / "sub"
    sub.mkdir(parents=True)
    entry = sub / "app.py"
    entry.write_text("print('nested')\n", encoding="utf-8")
    out_exe = proj / "nested_proj.exe"

    ok, out_path, log = bundler.bundle(
        project_dir=str(proj),
        entry_script=str(entry),
        output_exe=str(out_exe),
        target="win64",
        onefile=True,
    )
    assert ok, log
    import zipfile
    with zipfile.ZipFile(out_path, "r") as zf:
        names = set(zf.namelist())
        assert "nested_proj.asm" not in names
        assert "sub/app.py" in names
        assert 'sub\\app.py' in zf.read("run.bat").decode("utf-8")
        assert "sub/app.py" in zf.read("run.sh").decode("utf-8")

    exp_dir = tmp_path / "exported"
    FasmExporter.export("format ELF64 executable 3\nentry start\nstart:\nret\n", exp_dir, app_name="demo", target="linux")
    sh_txt = (exp_dir / "build.sh").read_text(encoding="ascii")
    assert "uname -s" in sh_txt
    assert "fasm.darwin" in sh_txt and "fasm.x64" in sh_txt


def test_ast_parser_library_matching_and_list_pop():
    analyzer = AstAnalyzer()
    mod = analyzer.parse_source("def f(arr):\n    return arr.pop()\n")
    assert not mod.has_library("pil")
    fn = mod.functions["f"]
    assert not fn.local_vars["arr"].var_type.is_dict()


def test_optimizer_safety_and_passes_run():
    opt = PeepholeOptimizer()
    asm = """
    push qword [rbp - 8]
    pop qword [rbp - 16]
    push rsp
    pop rax
    mov qword [rbp - 24], rcx
    mov rcx, qword [rbp - 24]
    ret
"""
    out = opt.optimize(asm)
    assert opt.passes_run >= 1
    assert "push qword [rbp - 8]" in out
    assert "pop qword [rbp - 16]" in out
    assert "push rsp" in out
    assert "mov rcx, qword [rbp - 24]" not in out


def test_runtime_static_abi_epilogue_and_clobbers():
    def split_funcs(txt: str):
        parts = re.split(r'(?m)^([a-zA-Z_][a-zA-Z0-9_]*:)', txt)
        return {parts[i][:-1]: parts[i + 1] for i in range(1, len(parts), 2)}

    modules = [
        ("WIN64_FULL", runtime_win64._get_win64_full_runtime_code()),
        ("WIN64_CONSOLE", runtime_win64._WIN64_CONSOLE_RUNTIME_CODE),
        ("WIN64_NET", runtime_win64._WIN64_NET_RUNTIME_CODE),
        ("LINUX", runtime_linux.get_linux_runtime_code()),
        ("MACOS", runtime_macos.get_macos_runtime_code()),
    ]
    for name, code in modules:
        for fname, body in split_funcs(code).items():
            lines = [l.split(";")[0].strip() for l in body.splitlines() if l.split(";")[0].strip()]
            has_rbp = any(re.match(r'^mov\s+rbp,\s*rsp$', l, re.I) for l in lines[:4])
            has_and_rsp = any(re.match(r'^and\s+rsp,\s*-16$', l, re.I) for l in lines[:15])
            if not has_rbp:
                continue
            saved = []
            sub_amt = None
            seen_rbp = False
            for l in lines[:18]:
                if re.match(r'^mov\s+rbp,\s*rsp$', l, re.I):
                    seen_rbp = True
                    continue
                if not seen_rbp:
                    continue
                mp = re.match(r'^push\s+(rbx|rsi|rdi|r12|r13|r14|r15)$', l, re.I)
                ms = re.match(r'^sub\s+rsp,\s*(\d+)$', l, re.I)
                ma = re.match(r'^and\s+rsp,\s*-16$', l, re.I)
                if mp:
                    saved.append(mp.group(1).lower())
                elif ms:
                    sub_amt = int(ms.group(1))
                elif ma:
                    continue
                else:
                    break
            if not saved:
                continue
            expected_off = len(saved) * 8
            for idx, l in enumerate(lines):
                if re.match(r'^ret$', l, re.I):
                    j = idx - 1
                    if j >= 0 and re.match(r'^pop\s+rbp$', lines[j], re.I):
                        j -= 1
                    if j >= 0 and re.match(r'^mov\s+rsp,\s*rbp$', lines[j], re.I):
                        j -= 1
                    if j >= 0 and lines[j].lower().startswith("xor"):
                        # e.g. _pyfasm_heappush shared .hp_ret: xor eax, eax; ret
                        continue
                    popped_rev = []
                    while j >= 0:
                        mp = re.match(r'^pop\s+(rbx|rsi|rdi|r12|r13|r14|r15)$', lines[j], re.I)
                        if mp:
                            popped_rev.append(mp.group(1).lower())
                            j -= 1
                        else:
                            break
                    assert popped_rev == saved, f"{name}.{fname} pop mismatch: saved={saved} popped={popped_rev}"
                    prev_instr = lines[j] if j >= 0 else ""
                    if has_and_rsp:
                        m_lea = re.match(r'^lea\s+rsp,\s*\[rbp\s*-\s*(\d+)\]$', prev_instr, re.I)
                        assert m_lea and int(m_lea.group(1)) == expected_off, (
                            f"{name}.{fname} and rsp,-16 epilogue mismatch: expected lea rsp, [rbp - {expected_off}], got {prev_instr!r}"
                        )
                    elif sub_amt is not None:
                        m_lea = re.match(r'^lea\s+rsp,\s*\[rbp\s*-\s*(\d+)\]$', prev_instr, re.I)
                        m_add = re.match(r'^add\s+rsp,\s*(\d+)$', prev_instr, re.I)
                        assert (m_lea and int(m_lea.group(1)) == expected_off) or (m_add and int(m_add.group(1)) == sub_amt), (
                            f"{name}.{fname} stack epilogue mismatch: sub={sub_amt}, got {prev_instr!r}"
                        )


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PE64 execution")
def test_win64_floor_div_mod_and_floats_and_strs(tmp_path: Path):
    code = """
def main() -> int:
    for a in [10, -10, -9]:
        for b in [3, -3]:
            print(a // b, a % b)

    print_float(0.05)
    print_float(1.000001)
    print_float(-0.005)
    print_float(4.0)

    eps: float = 1e-15
    zero: float = 0.0
    print(1 if eps > zero else 0)
    f1: float = 1e-13
    f2: float = 2e-13
    print(1 if f1 < f2 else 0)

    s1 = str(123)
    s2 = str(456)
    print(s1, s2)
    return 0
"""
    cpython = subprocess.run(
        [
            sys.executable,
            "-c",
            "for a in [10, -10, -9]:\n"
            "  for b in [3, -3]:\n"
            "    print(a // b, a % b)\n",
        ],
        capture_output=True,
        text=True,
    )
    assert cpython.returncode == 0
    expected_div_mod = cpython.stdout.strip().splitlines()

    res = _compile_and_run_win64(tmp_path, code, "math_float_str")
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[:6] == expected_div_mod
    assert lines[6] == "0.050000"
    assert lines[7] == "1.000001"
    assert lines[8] == "-0.005000"
    assert lines[9] == "4.0"
    assert lines[10] == "1"
    assert lines[11] == "1"
    assert lines[12] == "123 456"


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PE64 execution")
def test_win64_dicts_sets_negative_keys_tombstones_and_ranges(tmp_path: Path):
    code = """
def main() -> int:
    d = {-1: 42, -2: 99}
    print(d[-1], d[-2])

    s = {-1, -2, -100}
    print(1 if (-1 in s) else 0)
    print([-1, -2, -3])

    big = {}
    for i in range(60):
        big[i] = i * 10
    print(len(big), big[59])

    # Tombstone reuse under repeated add/remove cycles
    cyc = {}
    for round_i in range(20):
        for k in range(20):
            cyc[k] = round_i * 100 + k
        for k in range(20):
            cyc.pop(k)
    cyc[7] = 777
    popped_val = cyc.pop(7)
    missing_val = cyc.pop(999, -5)
    cyc[7] = 777
    print(len(cyc), cyc[7], popped_val, missing_val)

    r = list(range(300))
    print(len(r), sum(r))

    step_v = 3
    r2 = range(2, 15, step_v)
    print(len(r2), r2[0], r2[-1])
    return 0
"""
    res = _compile_and_run_win64(tmp_path, code, "dict_set_range")
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "42 99"
    assert lines[1] == "1"
    assert lines[2] == "[-1, -2, -3]"
    assert lines[3] == "60 590"
    assert lines[4] == "1 777 777 -5"
    assert lines[5] == "300 44850"
    assert lines[6] == "5 2 14"


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows DLL execution")
def test_win64_two_simultaneous_dlls_reloc_and_callee_saved_abi(tmp_path: Path):
    code1 = """
def sum_range_loop(n: int) -> int:
    total = 0
    for x in [1, 2, 3, 4, 5]:
        total = total + x * n
    return total
"""
    code2 = """
def scale_and_sum(a: int, b: int) -> int:
    items = [a, b, a + b]
    acc = 0
    for v in items:
        acc = acc + v
    return acc * 2
"""
    compiler = PyFasmCompiler()
    dll1 = tmp_path / "mod1.dll"
    dll2 = tmp_path / "mod2.dll"
    s1 = tmp_path / "mod1.py"
    s2 = tmp_path / "mod2.py"
    s1.write_text(code1, encoding="utf-8")
    s2.write_text(code2, encoding="utf-8")

    ok1, _, log1 = compiler.compile_file(str(s1), output_binary=str(dll1), target="dll")
    ok2, _, log2 = compiler.compile_file(str(s2), output_binary=str(dll2), target="dll")
    assert ok1, log1
    assert ok2, log2
    assert b".reloc" in dll1.read_bytes()
    assert b".reloc" in dll2.read_bytes()

    lib1 = ctypes.CDLL(str(dll1))
    lib2 = ctypes.CDLL(str(dll2))
    try:
        lib1.sum_range_loop.argtypes = [ctypes.c_longlong]
        lib1.sum_range_loop.restype = ctypes.c_longlong
        lib2.scale_and_sum.argtypes = [ctypes.c_longlong, ctypes.c_longlong]
        lib2.scale_and_sum.restype = ctypes.c_longlong

        assert lib1.sum_range_loop(10) == 150
        assert lib2.scale_and_sum(3, 7) == 40
        assert lib1.sum_range_loop(2) == 30
    finally:
        for lib in (lib2, lib1):
            if hasattr(lib, "_handle") and isinstance(lib._handle, int):
                ctypes.windll.kernel32.FreeLibrary(lib._handle)


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows PE64 execution")
def test_win64_str_concat_and_json_preserve_callee_saved(tmp_path: Path):
    code = """
import json

def main() -> int:
    acc = ""
    for i in range(10):
        acc = acc + str(i)
    parsed = json.loads('{"x": 12, "y": [3, 4]}')
    total = 0
    for v in parsed["y"]:
        total = total + v
    print(acc)
    print(parsed["x"] + total)
    return 0
"""
    res = _compile_and_run_win64(tmp_path, code, "str_json_abi")
    assert res.returncode == 0
    lines = res.stdout.strip().splitlines()
    assert lines[0] == "0123456789"
    assert lines[1] == "19"



def _make_ico(sizes):
    import struct as _struct
    images = []
    for w in sizes:
        bpp = 32
        dib = _struct.pack('<IIIHHIIIIII', 40, w, w * 2, 1, bpp, 0, w * w * 4 + w * w // 8, 0, 0, 0, 0)
        images.append((w, bpp, dib + bytes([w & 0xFF]) * (w * w * 4) + b'\x00' * (w * w // 8)))
    header = _struct.pack('<HHH', 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for w, bpp, blob in images:
        entries += _struct.pack('<BBBBHHII', w & 0xFF, w & 0xFF, 0, 0, 1, bpp, len(blob), offset + len(blobs))
        blobs += blob
    return header + entries + blobs


def test_icon_resource_inline_multi_image_and_invalid_input(tmp_path: Path):
    from pyfasm.icon_resource import build_icon_rsrc_section, parse_ico

    ico = _make_ico([16, 32])
    imgs = parse_ico(ico)
    assert [(i[0], i[5]) for i in imgs] == [(16, 32), (32, 32)]

    rsrc = build_icon_rsrc_section(ico)
    assert "resource _pyfasm_icons, 1, 0, _pyfasm_icon_data_1, 2, 0, _pyfasm_icon_data_2" in rsrc
    assert "_pyfasm_main_icon dd RVA _pyfasm_icon_group_hdr, 34, 0, 0" in rsrc
    assert "file " not in rsrc

    # Invalid / missing inputs never produce a broken .rsrc section
    assert build_icon_rsrc_section(b"\x89PNG not an ico") == ""
    assert build_icon_rsrc_section(tmp_path / "missing.ico") == ""
    assert build_icon_rsrc_section(None) == ""

    # Generated assembly is self-contained: it assembles even after the .ico is deleted
    from pyfasm.fasm_runner import FasmRunner

    icon_file = tmp_path / "icon.ico"
    icon_file.write_bytes(ico)
    for onefile in (True, False):
        launcher = ProjectBundler().generate_launcher_asm(
            entry_script=str(tmp_path / "app.py"), target="win64", onefile=onefile, icon_path=str(icon_file)
        )
        assert "_pyfasm_icon_bits_2:" in launcher
        assert "file " not in launcher.split("section '.rsrc'", 1)[1]
        icon_backup = icon_file.read_bytes()
        icon_file.unlink()
        out_exe = tmp_path / f"launcher_{int(onefile)}.exe"
        ok, log = FasmRunner().assemble(launcher, str(out_exe), asm_file_path=str(tmp_path / f"launcher_{int(onefile)}.asm"))
        assert ok, log
        icon_file.write_bytes(icon_backup)


def test_asm_files_written_without_py310_only_write_text_newline():
    # Path.write_text(newline=...) only exists on Python 3.10+, but pyfasm64 supports 3.8+.
    for rel in ("src/pyfasm/compiler.py", "src/pyfasm/fasm_runner.py", "src/pyfasm/bundler.py",
                "src/pyfasm/fasm_exporter.py", "src/pyfasm/codegen_x64.py", "src/pyfasm/cli.py"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert not re.search(r"write_text\([^)]*newline\s*=\s*[\"']", text), rel
