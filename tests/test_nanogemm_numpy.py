import pathlib
import textwrap
import pytest
from pyfasm.compiler import PyFasmCompiler


def test_nanogemm_and_numpy_integration(tmp_path):
    py_code = textwrap.dedent('''
        import nanogemm
        import numpy as np

        # Test 1: get_simd_isa()
        isa = nanogemm.get_simd_isa()
        assert "SIMD" in isa

        # Test 2: 1D dot product
        v1 = [1, 2, 3]
        v2 = [4, 5, 6]
        dot_res = nanogemm.matmul(v1, v2)
        assert dot_res == 32

        # Test 3: 2D matrix multiplication via nanogemm.matmul
        A = [[1, 2], [3, 4]]
        B = [[5, 6], [7, 8]]
        C = nanogemm.matmul(A, B)
        # C = [[19, 22], [43, 50]]
        assert C[0][0] == 19
        assert C[0][1] == 22
        assert C[1][0] == 43
        assert C[1][1] == 50

        # Test 4: Binary @ operator (ast.MatMult)
        D = A @ B
        assert D[0][0] == 19
        assert D[1][1] == 50

        # Test 5: np.zeros and np.ones
        z = np.zeros(5)
        assert len(z) == 5
        assert z[0] == 0

        z2d = np.zeros((2, 3))
        assert len(z2d) == 2
        assert len(z2d[0]) == 3
        assert z2d[1][2] == 0

        o = np.ones(4)
        assert len(o) == 4
        assert o[3] == 1

        print("All nanogemm and numpy tests passed!")
    ''').strip()
    compiler = PyFasmCompiler()
    src_file = tmp_path / "test_nanogemm.py"
    exe_file = tmp_path / "test_nanogemm.exe"
    src_file.write_text(py_code, encoding="utf-8")

    success, exe_path, log = compiler.compile_file(str(src_file), output_binary=str(exe_file))
    assert success, f"Compilation failed: {log}"
    exe_path = pathlib.Path(exe_path)
    assert exe_path.exists()

    import subprocess
    res = subprocess.run([str(exe_path)], capture_output=True, text=True, timeout=10)
    assert res.returncode == 0, f"Process failed with return code {res.returncode}, stderr: {res.stderr}"
    assert "All nanogemm and numpy tests passed!" in res.stdout
