"""
Regression tests for FastAPI handler parameters in the compiled win64 HTTP server:
1. A query parameter that is absent from the URL takes its declared default.
2. A parameter annotated as dict receives the parsed JSON request body.
"""
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

from pyfasm.compiler import PyFasmCompiler


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _get_json(url: str, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="GET" if data is None else "POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        assert resp.status == 200
        return json.loads(resp.read().decode("utf-8"))


def test_fastapi_default_params_and_json_body_win64(tmp_path: Path):
    launcher = []
    if sys.platform != "win32":
        wine = shutil.which("wine") or shutil.which("wine64")
        if not wine:
            pytest.skip("Wine is required to run the compiled Windows PE server")
        launcher = [wine]

    port = _free_local_port()
    source = f"""
from fastapi import FastAPI
import uvicorn

app = FastAPI()
store = {{}}

@app.get("/health")
def health():
    return {{"status": "ok"}}

@app.get("/page")
def page(limit: int = 10, offset: int = 0, tag: str = "all"):
    return {{"limit": limit, "offset": offset, "next": limit + offset, "tag": tag}}

@app.post("/users/{{uid}}")
def add_user(uid: int, body: dict):
    store[str(uid)] = body["name"]
    return {{"uid": uid, "name": body["name"], "age2": body["age"] * 2, "total": len(store)}}

@app.post("/echo")
def echo(payload: dict):
    return {{"got": payload}}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port={port})
"""
    src_file = tmp_path / "fastapi_params.py"
    src_file.write_text(source, encoding="utf-8")
    exe = tmp_path / "fastapi_params.exe"
    ok, _bin_path, log = PyFasmCompiler().compile_file(str(src_file), str(exe), target="win64")
    assert ok is True, f"Compilation failed:\n{log}"

    proc = subprocess.Popen(launcher + [str(exe)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        base_url = f"http://127.0.0.1:{port}"
        ready = False
        for _ in range(100):
            if proc.poll() is not None:
                out, err = proc.communicate()
                pytest.fail(
                    f"FastAPI server exited early ({proc.returncode}):\n"
                    f"{out.decode(errors='replace')}\n{err.decode(errors='replace')}"
                )
            try:
                ready = _get_json(f"{base_url}/health") == {"status": "ok"}
                break
            except OSError:
                time.sleep(0.1)
        assert ready, "Compiled FastAPI server did not start listening in time"

        assert _get_json(f"{base_url}/page") == {"limit": 10, "offset": 0, "next": 10, "tag": "all"}
        assert _get_json(f"{base_url}/page?limit=5") == {"limit": 5, "offset": 0, "next": 5, "tag": "all"}
        assert _get_json(f"{base_url}/page?offset=7&tag=x") == {
            "limit": 10,
            "offset": 7,
            "next": 17,
            "tag": "x",
        }

        assert _get_json(f"{base_url}/users/3", {"name": "ann", "age": 21}) == {
            "uid": 3,
            "name": "ann",
            "age2": 42,
            "total": 1,
        }
        assert _get_json(f"{base_url}/users/4", {"name": "bob", "age": 30})["total"] == 2

        nested = {"n": {"k": [1, 2]}, "s": "hi"}
        assert _get_json(f"{base_url}/echo", nested) == {"got": nested}
    finally:
        proc.kill()
        proc.wait(timeout=10)
        if launcher:
            wineserver = shutil.which("wineserver")
            if wineserver:
                subprocess.call([wineserver, "-k"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
