"""Vapi REST client. Every call is phone to phone: the target assistant dials a Vapi number
where the scripted caller assistant answers. Both sides are machines, so turn boundaries are clean."""
# --- windows-safe preamble: utf-8 console, load .env, readable API errors ---
import os as _os, sys as _sys
from pathlib import Path as _Path
try: _sys.stdout.reconfigure(encoding="utf-8", errors="replace"); _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
def _load_env():
    here = _Path(__file__).resolve().parent
    for p in (_Path.cwd() / ".env", here / ".env", here.parent / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line: continue
                k, v = line.split("=", 1); v = v.strip().strip('"').strip("'")
                if v: _os.environ.setdefault(k.strip(), v)
            return
_load_env()
def _ok(r):
    if r.status_code >= 400:
        raise SystemExit(f"API error {r.status_code} on {r.request.method} {r.url}\n{r.text[:800]}")
    return r
# --- end preamble ---

import time, requests

BASE = "https://api.vapi.ai"

def _h():
    return {"Authorization": f"Bearer {_os.environ['VAPI_API_KEY']}", "Content-Type": "application/json"}

def create_assistant(payload):
    return _ok(requests.post(f"{BASE}/assistant", headers=_h(), json=payload, timeout=30)).json()["id"]

def delete_assistant(aid):
    requests.delete(f"{BASE}/assistant/{aid}", headers=_h(), timeout=30)

def attach_to_number(phone_number_id, assistant_id):
    """Point an inbound Vapi number at an assistant (None to detach)."""
    _ok(requests.patch(f"{BASE}/phone-number/{phone_number_id}", headers=_h(), json={"assistantId": assistant_id}, timeout=30))

def from_number_id(telephony):
    key = "VAPI_FROM_TWILIO_NUMBER_ID" if telephony == "twilio" else "VAPI_FROM_NUMBER_ID"
    v = _os.environ.get(key)
    if not v: raise SystemExit(f"{key} is not set in .env (needed for telephony: {telephony})")
    return v

def start_call(target_assistant_id, telephony):
    body = {"assistantId": target_assistant_id, "phoneNumberId": from_number_id(telephony),
            "customer": {"number": _os.environ["VAPI_CALLEE_NUMBER"]}}
    return _ok(requests.post(f"{BASE}/call", headers=_h(), json=body, timeout=30)).json()["id"]

def wait_for_call(call_id, timeout_s=240):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        c = _ok(requests.get(f"{BASE}/call/{call_id}", headers=_h(), timeout=30)).json()
        if c.get("status") == "ended":
            return c
        time.sleep(3)
    raise TimeoutError(f"call {call_id} did not end in {timeout_s}s")

def artifact_messages(call):
    art = call.get("artifact") or {}
    return art.get("messages") or call.get("messages") or []
