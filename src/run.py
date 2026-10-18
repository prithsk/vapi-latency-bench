"""Run every config, record per-turn latency, write a dated results file."""
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

import json, time, traceback
sys = _sys
sys.path.insert(0, str(_Path(__file__).parent))
import config, measure, vapi

ROOT = _Path(__file__).parent.parent

def run_config(cfg, dry_run=False):
    base = {"config": cfg["name"], "telephony": cfg["telephony"], "model": cfg["model.model"], "voice": cfg["voice.provider"], "calls": 0, "turns": 0}
    if dry_run:
        return {**base, **measure.summarize([]), "note": "dry run"}
    lat, done = [], 0
    try:
        aid = vapi.create_assistant(config.target_payload(cfg))
    except SystemExit as e:
        print(f"  SKIP {cfg['name']}: {e}", flush=True)
        return {**base, **measure.summarize([]), "error": str(e)[:300]}
    try:
        for i in range(cfg["calls"]):
            try:
                call = vapi.wait_for_call(vapi.start_call(aid, cfg["telephony"]))
                got = measure.turn_latencies_ms(vapi.artifact_messages(call))
                lat += got; done += 1
                print(f"  {cfg['name']} call {i+1}/{cfg['calls']}: {len(got)} turns, ended: {call.get('endedReason')}", flush=True)
            except (SystemExit, TimeoutError) as e:
                print(f"  {cfg['name']} call {i+1} failed: {e}", flush=True)
            time.sleep(3)
    finally:
        vapi.delete_assistant(aid)
    return {**base, "calls": done, "turns": len(lat), **measure.summarize(lat)}

def table(rows):
    out = ["| Stack | Telephony | Calls | Turns | p50 ms | p95 ms | p99 ms |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        dash = lambda v: v if v is not None else "-"
        out.append(f"| {r['config']} | {r['telephony']} | {r['calls']} | {r['turns']} | {dash(r['p50'])} | {dash(r['p95'])} | {dash(r['p99'])} |")
    return "\n".join(out)

def main(dry_run=False):
    cfgs = config.load_all(ROOT / "configs")
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")]
    if only: cfgs = [c for c in cfgs if any(o in c["name"] for o in only[0].split(","))]
    if dry_run:
        print(table([run_config(c, True) for c in cfgs])); return
    for k in ("VAPI_API_KEY", "VAPI_CALLEE_NUMBER_ID", "VAPI_CALLEE_NUMBER", "VAPI_FROM_NUMBER_ID"):
        if not _os.environ.get(k): raise SystemExit(f"{k} is not set in .env")
    caller = vapi.create_assistant(config.caller_payload())
    vapi.attach_to_number(_os.environ["VAPI_CALLEE_NUMBER_ID"], caller)
    try:
        rows = [run_config(c) for c in cfgs]
    finally:
        vapi.attach_to_number(_os.environ["VAPI_CALLEE_NUMBER_ID"], None)
        vapi.delete_assistant(caller)
    stamp = time.strftime("%Y-%m-%d")
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / f"{stamp}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    t = table(rows)
    (ROOT / "results" / f"{stamp}.md").write_text(f"# Vapi latency bench, {stamp}\n\n{t}\n", encoding="utf-8")
    print(t)

if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
