"""Turn latency = time from the end of the user's utterance to the start of the
assistant's spoken reply. Computed from Vapi's call artifact, which carries a
timestamped transcript with role, start and end for every message.

Vapi's GET /call/{id} returns artifact.messages like:
  {"role": "user", "message": "...", "time": 1715000000123, "endTime": 1715000001456, ...}
  {"role": "bot",  "message": "...", "time": 1715000002001, "endTime": ..., ...}
`time` is the start of speech, `endTime` the end, both in epoch ms.
"""
from statistics import median

def _start(m):
    if m.get("time") is not None: return m["time"]
    if m.get("secondsFromStart") is not None: return m["secondsFromStart"] * 1000
    return None

def _end(m):
    if m.get("endTime") is not None: return m["endTime"]
    s = _start(m)
    if s is not None and m.get("duration") is not None: return s + m["duration"]
    return s

def turn_latencies_ms(messages):
    """Pair each user message with the next bot message; return bot start - user end.
    Reads epoch-ms time/endTime, falling back to secondsFromStart + duration."""
    out = []
    pending_user_end = None
    for m in messages:
        role = m.get("role")
        if role == "user":
            pending_user_end = _end(m)
        elif role in ("bot", "assistant") and pending_user_end is not None:
            start = _start(m)
            if start is not None and start >= pending_user_end:
                out.append(start - pending_user_end)
            pending_user_end = None
    return out

def percentile(values, p):
    if not values: return None
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k); c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)

def summarize(all_latencies_ms):
    v = [x for x in all_latencies_ms if x is not None]
    if not v:
        return {"n": 0, "p50": None, "p95": None, "p99": None, "min": None, "max": None}
    return {"n": len(v), "p50": round(median(v)), "p95": round(percentile(v, 95)),
            "p99": round(percentile(v, 99)), "min": min(v), "max": max(v)}
