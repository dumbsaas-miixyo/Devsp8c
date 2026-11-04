#!/usr/bin/env python3
"""
Devsp8c Desktop Agent - for a desktop that runs Android Studio.

What this is:
  A small, local agent that Devsp8c reaches ONLY through the WireGuard VPN.
  Devsp8c (10.8.0.20) -> VPN tunnel -> Desktop (10.8.0.10:18080) -> this agent
  -> local Android Studio / ADB / Gradle on that desktop.

What this is NOT:
  - It is NOT Android Studio itself, and it does NOT replace Android Studio.
  - It does NOT expose ADB (port 5037) or Android Studio to the internet.
  - It does NOT run arbitrary shell commands from the network.

Security rules built in:
  1. Bind ONLY to the VPN IP (default 10.8.0.10). Never bind to 0.0.0.0
     in production, or anyone on your LAN / internet could reach it.
  2. Every request needs:  Authorization: Bearer <DEVSP8C_AGENT_TOKEN>
     Set the token in an environment variable, never in code or git.
  3. Only allow-listed task types run, and project paths must be under
     DEVSP8C_WORKSPACE (default: ~/Devsp8cProjects).
  4. No packet contents, no key material, and no tokens are logged.

Network design (see README.md):
  VPN subnet:        10.8.0.0/24
  VPN server:        10.8.0.1   WireGuard UDP 51820
  Desktop client:    10.8.0.10  Agent TCP 18080 (VPN only)
  Devsp8c client:    10.8.0.20

  So Devsp8c uses:  http://10.8.0.10:18080/status
  WireGuard itself uses UDP 51820 on the server - that is a different port,
  for the tunnel, not for the agent.

Foreground vs background:
  - foreground: Devsp8c asks the agent to do something NOW and waits for
    the result, e.g. open a project in Android Studio, list ADB devices.
    On a desktop, "foreground" means: launch / bring the app to the front
    if the OS allows it. This agent cannot force-focus an app from a
    headless service on every OS - it launches it and reports back.
  - background: Devsp8c queues a long job (Gradle build, emulator start)
    and polls GET /task/<id> for status. The job keeps running after
    Devsp8c disconnects, until it finishes or is cancelled.

Usage on the desktop:
  export DEVSP8C_AGENT_TOKEN="a-long-random-token-you-generate"
  export DEVSP8C_WORKSPACE="$HOME/Devsp8cProjects"
  python3 agent.py --bind 10.8.0.10 --port 18080

  For a local test only (no VPN yet):
  python3 agent.py --bind 127.0.0.1 --port 18081

Requires: Python 3.11+, Android Studio / ADB / Gradle only if you use
those task types. No third-party Python packages.
"""

import argparse
import json
import os
import queue
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

# ---------------------------------------------------------------- config
TOKEN = os.environ.get("DEVSP8C_AGENT_TOKEN", "")
WORKSPACE = Path(os.environ.get("DEVSP8C_WORKSPACE", Path.home() / "Devsp8cProjects")).resolve()
WORKSPACE.mkdir(parents=True, exist_ok=True)

TASKS = {}  # id -> dict
TASK_LOCK = threading.Lock()
JOB_QUEUE: "queue.Queue[dict]" = queue.Queue()


def safe_project_path(project: str) -> Path:
    """Resolve a project path and refuse anything outside WORKSPACE."""
    p = (WORKSPACE / project).resolve() if not os.path.isabs(project) else Path(project).resolve()
    if WORKSPACE not in p.parents and p != WORKSPACE:
        raise ValueError("Project path is outside DEVSP8C_WORKSPACE")
    return p


def run(cmd, cwd=None, timeout=600):
    """Run an allow-listed local command, capture output, never shell=True."""
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None,
                            capture_output=True, text=True, timeout=timeout)
    return {"returncode": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:]}


def do_task(task):
    """Execute one task. Only these types are allowed - nothing else."""
    t = task["type"]
    project = task.get("project", "")
    try:
        if t == "status":
            return {"ok": True, "workspace": str(WORKSPACE),
                    "adb": _which("adb"), "gradle": _which("gradle")}

        if t == "adb_devices":
            if not _which("adb"):
                return {"ok": False, "error": "adb not found. Install Android Studio / platform-tools and add adb to PATH."}
            return {"ok": True, "result": run(["adb", "devices"])}

        if t == "open_project":
            # Launches Android Studio with the project. On Windows this is
            # 'studio64.exe', on macOS 'studio', on Linux 'studio.sh'.
            # The agent tries the common names in order.
            path = safe_project_path(project)
            if not path.exists():
                return {"ok": False, "error": f"Project not found: {path}"}
            studio = _which("studio") or _which("studio64") or _which("studio.sh")
            if not studio:
                return {"ok": False,
                        "error": "Android Studio launcher not in PATH. Open Android Studio once, or add its bin folder to PATH, then retry."}
            # Popen, not wait: this is a foreground launch, Devsp8c polls status separately.
            subprocess.Popen([studio, str(path)])
            return {"ok": True, "result": f"Launched Android Studio with {path}"}

        if t == "gradle_build":
            path = safe_project_path(project)
            gradlew = path / ("gradlew.bat" if os.name == "nt" else "gradlew")
            if not gradlew.exists():
                return {"ok": False, "error": f"No gradlew in {path}. Is this an Android/Gradle project?"}
            return {"ok": True, "result": run([str(gradlew), "assembleDebug"], cwd=path, timeout=1800)}

        if t == "start_emulator":
            if not _which("emulator"):
                return {"ok": False, "error": "emulator not found. Install it via Android Studio SDK Manager."}
            avd = task.get("avd", "")
            if not avd:
                return {"ok": False, "error": "Missing 'avd' name. List AVDs with: emulator -list-avds"}
            subprocess.Popen(["emulator", "-avd", avd])
            return {"ok": True, "result": f"Started emulator AVD: {avd}"}

        return {"ok": False, "error": f"Unknown task type: {t}"}
    except Exception as exc:  # keep the agent alive on a bad task
        return {"ok": False, "error": str(exc)}


def _which(name):
    import shutil
    return shutil.which(name)


def worker():
    while True:
        task = JOB_QUEUE.get()
        with TASK_LOCK:
            task["status"] = "running"
            task["started_at"] = time.time()
        result = do_task(task)
        with TASK_LOCK:
            task["status"] = "done" if result.get("ok") else "failed"
            task["result"] = result
            task["finished_at"] = time.time()
        JOB_QUEUE.task_done()


# ------------------------------------------------------------------- HTTP
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        # Metadata only: method + path, never headers, tokens or bodies.
        print(f"{self.client_address[0]} {self.command} {self.path}", flush=True)

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth(self):
        if not TOKEN:
            return False
        return self.headers.get("Authorization") == f"Bearer {TOKEN}"

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        if not self._auth():
            return self._send(401, {"ok": False, "error": "Unauthorized. Set DEVSP8C_AGENT_TOKEN on the desktop and send it as a Bearer token."})
        path = urlparse(self.path).path
        if path == "/status":
            return self._send(200, {"ok": True, "agent": "devsp8c-desktop-agent",
                                    "mode": "vpn-only", "workspace": str(WORKSPACE)})
        if path.startswith("/task/"):
            task_id = path.split("/task/")[1]
            with TASK_LOCK:
                task = TASKS.get(task_id)
            if not task:
                return self._send(404, {"ok": False, "error": "Task not found"})
            return self._send(200, {"ok": True, "task": task})
        return self._send(404, {"ok": False, "error": "Unknown endpoint"})

    def do_POST(self):
        if not self._auth():
            return self._send(401, {"ok": False, "error": "Unauthorized"})
        path = urlparse(self.path).path
        if path != "/task":
            return self._send(404, {"ok": False, "error": "Unknown endpoint"})
        try:
            body = self._read_json()
        except Exception:
            return self._send(400, {"ok": False, "error": "Invalid JSON"})
        task_type = body.get("type", "")
        allowed = {"status", "adb_devices", "open_project", "gradle_build", "start_emulator"}
        if task_type not in allowed:
            return self._send(400, {"ok": False, "error": f"Task type not allowed. Allowed: {sorted(allowed)}"})
        mode = body.get("mode", "foreground")  # foreground | background
        task = {"id": str(uuid.uuid4()), "type": task_type, "mode": mode,
                "project": body.get("project", ""), "avd": body.get("avd", ""),
                "status": "queued", "created_at": time.time()}
        with TASK_LOCK:
            TASKS[task["id"]] = task
        if mode == "background":
            JOB_QUEUE.put(task)
            return self._send(202, {"ok": True, "task_id": task["id"], "status": "queued",
                                    "poll": f"GET /task/{task['id']}"})
        # Foreground: run now, in a worker thread, wait up to 30s for a quick result.
        # Long foreground jobs (Gradle) should be sent as background instead.
        JOB_QUEUE.put(task)
        for _ in range(300):
            with TASK_LOCK:
                if TASKS[task["id"]]["status"] in ("done", "failed"):
                    return self._send(200, {"ok": True, "task": TASKS[task["id"]]})
            time.sleep(0.1)
        return self._send(202, {"ok": True, "task_id": task["id"], "status": "running",
                                "note": "Still running. Poll GET /task/<id>."})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="10.8.0.10", help="VPN IP of this desktop, e.g. 10.8.0.10")
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()
    if not TOKEN:
        print("WARNING: DEVSP8C_AGENT_TOKEN is not set. The agent will reject all requests until you set it.")
    print(f"Devsp8c Desktop Agent listening on {args.bind}:{args.port} (VPN only)")
    print(f"Workspace: {WORKSPACE}")
    print("Devsp8c should call: http://" + args.bind + f":{args.port}/status  with a Bearer token")
    threading.Thread(target=worker, daemon=True).start()
    ThreadingHTTPServer((args.bind, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
