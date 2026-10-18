import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import measure, config

# six turns, varied gaps, one bot message with no preceding user (firstMessage) that must be ignored
msgs = [
  {"role":"bot","message":"Ready.","time":1000,"endTime":1400},
  {"role":"user","message":"capital of france","time":2000,"endTime":2800},
  {"role":"bot","message":"Paris.","time":3450,"endTime":3900},          # 650
  {"role":"user","message":"count","time":5000,"endTime":5600},
  {"role":"bot","message":"one two three four five","time":6900,"endTime":8000},  # 1300
  {"role":"user","message":"after tuesday","time":9000,"endTime":9500},
  {"role":"bot","message":"Wednesday.","time":9950,"endTime":10300},    # 450
  {"role":"user","message":"spell latency","time":11000,"endTime":11800},
  {"role":"bot","message":"L A T E N C Y","time":14800,"endTime":16000},  # 3000 spike
  {"role":"user","message":"sides of a triangle","time":17000,"endTime":17600},
  {"role":"bot","message":"Three.","time":18200,"endTime":18500},        # 600
  {"role":"user","message":"goodbye","time":19000,"endTime":19300},
  {"role":"bot","message":"Goodbye.","time":19900,"endTime":20200},     # 600
]
lat = measure.turn_latencies_ms(msgs)
assert lat == [650, 1300, 450, 3000, 600, 600], lat
s = measure.summarize(lat)
assert s["n"] == 6 and s["p50"] == 625 and s["max"] == 3000, s
assert s["p95"] > 2000, s          # the spike shows up in p95, not p50 — the whole point
assert measure.summarize([]) == {"n":0,"p50":None,"p95":None,"p99":None,"min":None,"max":None}
# two user msgs in a row (interruption): only the latest end counts
assert measure.turn_latencies_ms([{"role":"user","time":1,"endTime":5},{"role":"user","time":6,"endTime":9},{"role":"bot","time":12}]) == [3]
# bot before user end (overlap/barge-in) is dropped, not negative
assert measure.turn_latencies_ms([{"role":"user","time":1,"endTime":10},{"role":"bot","time":8}]) == []
# config parsing + assistant payload
cfgs = config.load_all(str(Path(__file__).parent.parent / "configs"))
assert len([c for c in cfgs if not c["name"].startswith("tune-")]) == 6 and len(cfgs) == 9
tw = [c for c in cfgs if c["telephony"] == "twilio"]; assert len(tw) == 3
assert {c["telephony"] for c in cfgs} == {"vapi", "twilio"}
p = config.target_payload(cfgs[0])
assert p["model"]["temperature"] == 0 and p["transcriber"]["provider"] == "deepgram"
el = [config.target_payload(c) for c in cfgs if c["voice.provider"] == "11labs"][0]["voice"]
assert el["voiceId"] == "21m00Tcm4TlvDq8ikWAM" and el["model"] == "eleven_turbo_v2_5"   # voiceId is a voice, model is a model
vv = [config.target_payload(c) for c in cfgs if c["voice.provider"] == "vapi"][0]["voice"]
assert "model" not in vv
cp = config.caller_payload()
assert cp["firstMessageMode"] == "assistant-waits-for-user" and "Thanks, bye." in cp["endCallPhrases"]
assert all(q in cp["model"]["messages"][0]["content"] for q in config.SCRIPT)
# secondsFromStart fallback when epoch fields are missing
fb = [{"role":"user","secondsFromStart":2.0,"duration":800},{"role":"bot","secondsFromStart":3.45}]
assert measure.turn_latencies_ms(fb) == [650.0], measure.turn_latencies_ms(fb)
assert len(config.SCRIPT) == 6

tc = {c["name"]: c for c in config.load_all(str(Path(__file__).parent.parent / "configs"))}
d = config.target_payload(tc["tune-0-default-vapi"]); assert "startSpeakingPlan" not in d
w = config.target_payload(tc["tune-1-wait0-vapi"]); assert w["startSpeakingPlan"] == {"waitSeconds": 0} and w["voice"]["model"] == "eleven_turbo_v2_5"
e = config.target_payload(tc["tune-2-wait0-endpointing-vapi"]); assert e["startSpeakingPlan"]["transcriptionEndpointingPlan"]["onNoPunctuationSeconds"] == 0.8
assert {k: v for k, v in d.items() if k != "name"} == {k: v for k, v in w.items() if k not in ("name", "startSpeakingPlan")}   # only the knob differs
print("tuning tests passed")
print("all tests passed")
