"""PyFASM Example 10: High-Performance Native HTTP Microservice (FastAPI)
Compiles a REST API service running on native OS Winsock2 sockets without asyncio overhead.

Compile with:
    pyfasm64 compile examples/10_fastapi_server.py -o api_server.exe
"""

from fastapi import FastAPI

app = FastAPI(title="PyFASM Native Server", version="1.1.0")

@app.get("/")
def read_root():
    return {"message": "Hello from native PyFASM HTTP server!", "status": "online"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "engine": "PyFASM x86-64 Native"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
