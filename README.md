# vapi-latency-bench

An open benchmark for Vapi voice-agent latency, per stack, with p50 and p95.

Every thread about Vapi says the same thing: latency depends on the transcriber, the model, the voice, and the telephony path, and nobody publishes numbers. One developer ran 760 calls over four months to get one. This runs six stacks, ten calls each, six turns per call, and prints the table.

## Results

<!-- results:start -->
_Run `python src/run.py` to populate. Results land in `results/YYYY-MM-DD.md`._
<!-- results:end -->

## What's measured

**Turn latency** is the gap between the end of the caller's utterance and the start of the assistant's spoken reply, in milliseconds, read from the timestamped transcript in Vapi's call artifact. It's reported as p50 and p95, not mean, because the complaint is variance.

Both sides of the call are machines. The target assistant is built from the config and dials a Vapi number. On that number sits a scripted caller assistant that waits, then asks six fixed questions with one-sentence answers and no tools, then hangs up. So the number is the pipeline, not the model thinking.

## The six stacks

| Config | Transcriber | Model | Voice | Telephony |
|---|---|---|---|---|
| deepgram-gpt4omini-elevenlabs-vapi | Deepgram nova-3 | gpt-4o-mini | ElevenLabs turbo v2.5 | Vapi number |
| deepgram-gpt4omini-elevenlabs-twilio | same | same | same | Twilio number |
| deepgram-gpt4o-elevenlabs-vapi | Deepgram nova-3 | gpt-4o | ElevenLabs turbo v2.5 | Vapi number |
| deepgram-gpt4o-elevenlabs-twilio | same | same | same | Twilio number |
| deepgram-claude-sonnet-vapivoice-vapi | Deepgram nova-3 | claude-sonnet-4-5 | Vapi Elliot | Vapi number |
| deepgram-claude-sonnet-vapivoice-twilio | same | same | same | Twilio number |

Vapi number vs Twilio number for the same stack is the pair that matters; that's the jump users report.

Add a stack by dropping a markdown file in `configs/`. If Vapi rejects a model or voice id, the run prints Vapi's error, skips that config, and keeps going.

## Run it

Vapi dashboard: create a private API key, and create two free phone numbers. One gets dialed; the script attaches the scripted caller to it for the run and detaches after. The other is the outbound number for the `vapi` configs. For the `twilio` configs, import a Twilio number too, or delete the `*-twilio.md` files.

```
pip install -r requirements.txt
cp .env.example .env        # fill in the key and the number ids
python src/run.py --dry-run # empty table, no calls
python src/run.py           # ~60 calls, ~25 minutes, a few dollars
```

Results write to `results/<date>.json` and `results/<date>.md`.

## Files

```
configs/*.md        six stacks, one table each
src/config.py       reads a config, builds the target and the scripted caller, holds the six questions
src/vapi.py         create assistants, attach the caller to a number, place the call, wait, fetch the artifact
src/measure.py      pure functions: turn latencies from timestamps, percentiles
src/run.py          loop configs → calls → table
tests/test_measure.py
```

`measure.py` is the part worth reading. It pairs each user utterance with the next bot utterance, drops barge-ins where the bot started before the user finished, and only counts the latest user end when the user spoke twice.

## Caveats

Each config gets 10 calls of about 6 turns, roughly 60 measured turns. That is enough for a solid p50 and a usable p95. At 60 turns, p99 is essentially the single slowest turn, so read it as one worst-case sample. Provider latency drifts over the day, so results are dated and a run is a snapshot. Rerun before you cite.

## License

MIT
