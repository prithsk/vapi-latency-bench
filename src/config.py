import json
from pathlib import Path

def _merge(a, b):
    for k, v in b.items():
        a[k] = _merge(a.get(k, {}), v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return a

def load(path):
    rows = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not line.startswith("|") or "---" in line: continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] == "field": continue
        rows[cells[0]] = cells[1]
    rows["name"] = Path(path).stem
    rows["calls"] = int(rows.get("calls", 10))
    rows["turns_per_call"] = int(rows.get("turns_per_call", 6))
    return rows

def load_all(folder="configs"):
    return [load(p) for p in sorted(Path(folder).glob("*.md")) if p.name != "README.md"]

# The same six prompts every time. Short, factual, no tools, so the number is the pipeline.
SCRIPT = [
    "What is the capital of France?",
    "Say the numbers one through five.",
    "What day comes after Tuesday?",
    "Spell the word latency.",
    "How many sides does a triangle have?",
    "Say goodbye.",
]

def _voice(cfg):
    v = {"provider": cfg["voice.provider"], "voiceId": cfg["voice.voiceId"]}
    if cfg.get("voice.model"): v["model"] = cfg["voice.model"]
    return v

def target_payload(cfg):
    """The assistant under test. It places the call and answers the caller's questions."""
    return {
        "name": f"bench-{cfg['name']}"[:40],
        "firstMessage": "Ready.",
        "transcriber": {"provider": cfg["transcriber.provider"], "model": cfg["transcriber.model"]},
        "model": {"provider": cfg["model.provider"], "model": cfg["model.model"], "temperature": 0,
                  "messages": [{"role": "system", "content":
                      "You are a latency test target. Answer every question in one short sentence. "
                      "Never ask questions. Never call tools."}]},
        "voice": _voice(cfg),
        "maxDurationSeconds": 150,
    } if not cfg.get("extra") else _merge(target_payload({**cfg, "extra": ""}), json.loads(cfg["extra"]))

def caller_payload():
    """The scripted 'user'. It sits on the callee number, waits, then asks the six questions in order."""
    qs = "\n".join(f"{i+1}. {q}" for i, q in enumerate(SCRIPT))
    return {
        "name": "bench-scripted-caller",
        "firstMessageMode": "assistant-waits-for-user",
        "transcriber": {"provider": "deepgram", "model": "nova-3"},
        "model": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0,
                  "messages": [{"role": "system", "content":
                      "You are a test caller. Each time the other side finishes speaking, say exactly the next "
                      "question from this list, word for word, and nothing else:\n" + qs +
                      "\nAfter the answer to question 6, say exactly: Thanks, bye."}]},
        "voice": {"provider": "vapi", "voiceId": "Elliot"},
        "endCallPhrases": ["Thanks, bye."],
        "maxDurationSeconds": 150,
    }
