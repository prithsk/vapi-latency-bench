One markdown file per stack. Ten rows. The bench builds a Vapi assistant from the table and places `calls` real phone calls with it.

`telephony: vapi` dials out from a free Vapi number. `telephony: twilio` dials out from a Twilio number you imported into Vapi, which is where users report the latency jump. If you have no Twilio number, delete the `*-twilio.md` files.

Model and voice ids change over time. If Vapi rejects one, the run prints Vapi's error for that config, skips it, and keeps going. Fix the id in the file and rerun.
