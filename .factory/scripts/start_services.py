"""Start backend and frontend services."""
import subprocess
import time
import urllib.request
import os
import sys

def start_backend():
    env = os.environ.copy()
    proc = subprocess.Popen(
        [r"C:\EthicalSiteInspector\backend\.venv\Scripts\python.exe", "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
        cwd=r"C:\EthicalSiteInspector\backend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=env,
    )
    print(f"Backend started PID={proc.pid}")
    return proc

def start_frontend():
    proc = subprocess.Popen(
        ["cmd", "/c", "npx vite --port 5173 --host 127.0.0.1"],
        cwd=r"C:\EthicalSiteInspector\frontend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"Frontend started PID={proc.pid}")
    return proc

def wait_for_service(url, name, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = urllib.request.urlopen(url, timeout=3)
            if resp.status == 200:
                print(f"{name} is UP at {url}")
                return True
        except Exception:
            pass
        time.sleep(1)
    print(f"{name} FAILED to start within {timeout}s")
    return False

if __name__ == "__main__":
    bp = start_backend()
    fp = start_frontend()
    
    b_ok = wait_for_service("http://127.0.0.1:8000/api/health", "Backend")
    f_ok = wait_for_service("http://127.0.0.1:5173", "Frontend")
    
    if b_ok and f_ok:
        print("ALL_SERVICES_UP")
        # Write PIDs to file
        with open(r"C:\EthicalSiteInspector\.factory\scripts\pids.txt", "w") as f:
            f.write(f"{bp.pid}\n{fp.pid}\n")
    else:
        print("SERVICES_FAILED")
        sys.exit(1)
