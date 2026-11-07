import subprocess
from pathlib import Path
from pyfasm.compiler import PyFasmCompiler


def test_codewars_subpattern_lambda_gcd_set(tmp_path: Path):
    source = """
has_subpattern = lambda st, g=__import__('math').gcd: g(*map(st.count, set(st))) > 1

assert has_subpattern("a") == False, 'Input: "a"'
assert has_subpattern("AA") == True, 'Input: "AA"'
assert has_subpattern("444") == True, 'Input: "444"'
assert has_subpattern("aaaa") == True, 'Input: "aaaa"'
assert has_subpattern("abcd") == False, 'Input: "abcd"'
assert has_subpattern("babababababababa") == True, 'Input: "babababababababa"'
assert has_subpattern("bbabbaaabbaaaabb") == True, 'Input: "bbabbaaabbaaaabb"'
assert has_subpattern("ababababa") == False, 'Input: "ababababa"'
assert has_subpattern("aaaabb") == True, 'Input: "aaaabb"'
assert has_subpattern("abbb") == False, 'Input: "abbb"'
assert has_subpattern("123a123a123a") == True, 'Input: "123a123a123a"'
assert has_subpattern("123A123a123a") == False, 'Input: "123A123a123a"'
assert has_subpattern("12aa13a21233") == True, 'Input: "12aa13a21233"'
assert has_subpattern("12aa13a21233A") == False, 'Input: "12aa13a21233A"'
assert has_subpattern("aabbbbbbaa") == True, 'Input: "aabbbbbbaa"'
assert has_subpattern("abcdabcaccd") == False, 'Input: "abcdabcaccd"'
assert has_subpattern("aaabbbccccdddddd") == False, 'Input: "aaabbbccccdddddd"'
assert has_subpattern("aaabbbccccdddddddd") == False, 'Input: "aaabbbccccdddddddd"'

print("All subpattern test cases passed successfully.")
"""
    src_file = tmp_path / "subpattern_test.py"
    src_file.write_text(source, encoding="utf-8")
    out_exe = tmp_path / "subpattern_test.exe"

    compiler = PyFasmCompiler()
    ok, bin_path, log = compiler.compile_file(str(src_file), str(out_exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"
    assert out_exe.exists()

    res = subprocess.run([str(out_exe)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "All subpattern test cases passed successfully." in res.stdout
