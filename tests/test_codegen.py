import pytest
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_codegen_emits_valid_asm_structure():
    source = """
def main() -> int:
    x = 42
    print(x)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    assert "format PE64 console 5.0" in asm
    assert "_pyfasm_entry_point:" in asm
    assert "main:" in asm
    assert "call _pyfasm_print_int" in asm
    assert "call [ExitProcess]" in asm


def test_codegen_linux_elf64_structure():
    source = """
def main() -> int:
    x = 100
    print(x)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="linux")

    assert "format ELF64 executable 3" in asm
    assert "segment readable executable" in asm
    assert "syscall" in asm
    assert "main:" in asm


def test_codegen_macos_macho64_structure():
    source = """
def main() -> int:
    x = 200
    print(x)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="macos")

    assert "format binary as 'macho'" in asm
    assert "MH_MAGIC_64" in asm or "0xFEEDFACF" in asm
    assert "LC_SEGMENT_64" in asm or "0x19" in asm
    assert "syscall" in asm
    assert "main:" in asm


def test_codegen_escapes_reserved_fasm_keywords(tmp_path: Path):
    source = """
def add(a: int, b: int) -> int:
    return a + b

def test(x: int) -> int:
    return x * 2

def main() -> int:
    s = add(10, 20)
    t = test(s)
    print(t)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    assert "fn_add:" in asm
    assert "fn_test:" in asm
    assert "call fn_add" in asm
    assert "call fn_test" in asm

    # Verify that FASM compiles it without 'reserved word used as symbol'
    src_file = tmp_path / "reserved_app.py"
    src_file.write_text(source, encoding="utf-8")
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Compilation with reserved keywords failed: {log}"


def test_codegen_emits_fallback_stubs_for_unresolved_symbols(tmp_path: Path):
    source = """
def main() -> int:
    p = Path('myfile.txt')
    print(123)
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    assert "call Path" in asm
    assert "Path:" in asm
    assert "fallback stub for external symbol 'Path'" in asm

    # Verify that FASM compiles the code with unresolved symbol stubs without error
    src_file = tmp_path / "stub_app.py"
    src_file.write_text(source, encoding="utf-8")
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Compilation with external symbol stub failed: {log}"


def test_codegen_handles_numeric_prefix_and_invalid_symbols(tmp_path: Path):
    from pyfasm.codegen_x64 import safe_asm_label
    assert safe_asm_label("01_hello") == "_01_hello"
    assert safe_asm_label("123_calc") == "_123_calc"
    assert safe_asm_label("bad-symbol-name!") == "bad_symbol_name_"
    assert safe_asm_label("add") == "fn_add"

    source = """
def helper() -> int:
    return 777

def main() -> int:
    print(helper())
    return 0
"""
    src_file = tmp_path / "01_numeric_app.py"
    src_file.write_text(source, encoding="utf-8")
    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Compilation of numeric-prefixed file failed: {log}"


def test_codegen_handles_boolean_constants_and_instruction_shadowing(tmp_path: Path):
    source = """
def main() -> int:
    flag = False
    flag_on = True
    s = str(123)
    if flag:
        return 1
    return 0
"""
    src_file = tmp_path / "bool_and_str.py"
    src_file.write_text(source, encoding="utf-8")
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")
    assert "mov rax, 0" in asm
    assert "mov rax, 1" in asm
    assert "call fn_str" in asm
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Compilation failed: {log}"


def test_codegen_class_compilation_and_methods(tmp_path: Path):
    source = """
class Calculator:
    def __init__(self, val: int):
        self.val = val

    def add(self, x: int) -> int:
        return self.val + x

def main() -> int:
    calc = Calculator(100)
    res = calc.add(25)
    print(res)
    return 0
"""
    src_file = tmp_path / "calc_class.py"
    src_file.write_text(source, encoding="utf-8")
    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Class compilation failed: {log}"
    assert Path(bin_path).exists()

    # Verify execution output
    import sys
    if sys.platform == "win32":
        import subprocess
        res = subprocess.run([bin_path], capture_output=True, text=True, timeout=5)
        assert res.returncode == 0
        assert "125" in res.stdout


def test_codegen_modular_asm_folder_structure(tmp_path: Path):
    source = """
def add(a: int, b: int) -> int:
    return a + b

def main() -> int:
    print(add(10, 20))
    return 0
"""
    proj_dir = tmp_path / "my_project"
    proj_dir.mkdir()
    src_file = proj_dir / "main.py"
    src_file.write_text(source, encoding="utf-8")

    compiler = PyFasmCompiler()
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Compilation failed: {log}"

    # Verify that asm folder was cleanly created
    asm_dir = proj_dir / "asm"
    assert asm_dir.exists() and asm_dir.is_dir()
    assert (asm_dir / "main.asm").exists()
    assert (asm_dir / "constants.inc").exists()
    assert (asm_dir / "runtime.inc").exists()
    assert (asm_dir / "functions.inc").exists()
    assert (asm_dir / "imports.inc").exists()

    # Verify that project root does NOT have loose .asm files
    root_asm_files = list(proj_dir.glob("*.asm"))
    assert len(root_asm_files) == 0, f"Found loose .asm files in project root: {root_asm_files}"


def test_codegen_gui_window_calls_in_asm(tmp_path: Path):
    source = """
class MyWindowApp:
    def __init__(self):
        pass

    def mainloop(self):
        pass

def main() -> int:
    app = MyWindowApp()
    alert("Test Message", "Test Title")
    app.mainloop()
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    assert "call _pyfasm_init_gui" in asm
    assert "call _pyfasm_message_box" in asm
    assert "call _pyfasm_run_window_loop" in asm

    src_file = tmp_path / "gui_app.py"
    src_file.write_text(source, encoding="utf-8")
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"GUI compilation failed: {log}"


def test_codegen_multi_class_method_namespacing_and_window_title(tmp_path: Path):
    source = """
class ChildComponent:
    def __init__(self):
        self.setup_ui()

    def setup_ui(self):
        pass

class ParentWindow:
    def __init__(self):
        self.title("My Test App")
        self.setup_ui()

    def setup_ui(self):
        c = ChildComponent()

def main() -> int:
    win = ParentWindow()
    return 0
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    # Verify both methods are separately namespaced
    assert "ChildComponent_setup_ui" in asm
    assert "ParentWindow_setup_ui" in asm
    assert "call _pyfasm_set_window_title" in asm

    src_file = tmp_path / "multi_class.py"
    src_file.write_text(source, encoding="utf-8")
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Multi-class compilation failed: {log}"

    import sys
    if sys.platform == "win32":
        import subprocess
        res = subprocess.run([bin_path], capture_output=True, text=True, timeout=5)
        assert res.returncode == 0


def test_native_win32_ui_controls(tmp_path: Path):
    source = """
import customtkinter as ctk

class DemoApp(ctk.CTk):
    def __init__(self):
        self.title("Native Demo")
        self.lbl = ctk.CTkLabel(self, text="Header Title")
        self.entry = ctk.CTkEntry(self, placeholder_text="Type query...")
        self.btn = ctk.CTkButton(self, text="Search", command=self.do_action)
        self.lst = ctk.CTkScrollableFrame(self)

    def do_action(self):
        q = self.entry.get()
        self.entry.delete(0, "end")

def main():
    app = DemoApp()
    app.mainloop()
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    assert "call _pyfasm_create_label" in asm
    assert "call _pyfasm_create_edit" in asm
    assert "call _pyfasm_create_button" in asm
    assert "call _pyfasm_create_listbox" in asm
    assert "call _pyfasm_get_edit_text" in asm
    assert "call _pyfasm_run_window_loop" in asm

    src_file = tmp_path / "gui_demo.py"
    src_file.write_text(source, encoding="utf-8")
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"GUI compilation failed: {log}"


def test_background_tray_app_codegen(tmp_path: Path):
    source = """
import pystray

class PuntoSwitcher:
    def __init__(self):
        pass

    def run(self):
        pass

def main():
    app = PuntoSwitcher()
    app.run()
"""
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    # Verify tray initialization and event loop
    assert "call _pyfasm_init_tray" in asm
    assert "call _pyfasm_run_tray_loop" in asm
    # Verify NO window is created for tray apps!
    assert "call _pyfasm_ensure_window" not in asm
    assert "call _pyfasm_run_window_loop" not in asm

    src_file = tmp_path / "tray_app.py"
    src_file.write_text(source, encoding="utf-8")
    success, bin_path, log = compiler.compile_file(str(src_file), target="win64")
    assert success is True, f"Tray compilation failed: {log}"




def test_library_detection_and_adaptation(tmp_path: Path):
    from pyfasm.ast_parser import AstAnalyzer
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('''
[project]
name = "demo"
dependencies = [
    "customtkinter>=5.2.0",
    "requests",
    "pystray"
]
''', encoding="utf-8")

    src = tmp_path / "app.py"
    src.write_text('''
import pystray
import customtkinter as ctk

class App:
    pass
''', encoding="utf-8")

    analyzer = AstAnalyzer(project_root=tmp_path)
    module = analyzer.parse_file(src, project_root=tmp_path)

    assert module.has_library("customtkinter") is True
    assert module.has_library("requests") is True
    assert module.has_library("pystray") is True
    assert module.is_modern_gui is True
    assert module.is_tray_app is True
    assert module.is_http_app is True


def test_tray_app_self_icon_run_no_recursion(tmp_path: Path):
    source = '''
import pystray

class PuntoSwitcher:
    def __init__(self):
        self.icon = None

    def run(self):
        self.icon.run()

def main():
    app = PuntoSwitcher()
    app.run()
'''
    compiler = PyFasmCompiler()
    asm = compiler.compile_source_to_asm(source, target="win64")

    # In PuntoSwitcher_run, self.icon.run() MUST NOT call PuntoSwitcher_run recursively!
    func_body = asm.split("PuntoSwitcher_run:")[1].split(".epilog_PuntoSwitcher_run:")[0]
    assert "call PuntoSwitcher_run" not in func_body, "Infinite recursion detected in PuntoSwitcher_run!"
    assert "call _pyfasm_run_tray_loop" in func_body, "Tray loop should be called directly on self.icon.run()!"


def test_owner_drawn_cards_and_ansi_set_text():
    compiler = PyFasmCompiler()
    source = '''
import customtkinter as ctk

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.entry = ctk.CTkEntry(self)
        self.entry.delete(0, 10)

def main():
    app = App()
    app.mainloop()
'''
    asm = compiler.compile_source_to_asm(source, target="win64")
    # Verify owner-drawn listbox and measureitem
    assert "50200151h" in asm or "LBS_OWNERDRAWFIXED" in asm
    assert "WM_MEASUREITEM" in asm or "2Ch" in asm
    assert "_pyfasm_set_text" in asm
    assert "SetWindowTextA" in asm
    assert "SendMessageA" in asm
