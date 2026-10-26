# Retained transcription measurements

This directory holds selected strict-JSON output from the Spike 001 runner. A
filename or successful unit test is not a runtime claim: inspect each result's
status, trial errors, effective settings and fingerprints, and read the sibling
`FINDINGS.md` once measurements have been interpreted.

The four measured arms are Parakeet endpoint/hybrid and Nemotron
endpoint/native-stream.
Each uses a fresh process, one persistent loaded model, real-paced public audio,
one warmup pass and two measured repetitions. Warmups are not headline trials.
Natural fixtures and derived repeat/switch assemblies must be interpreted
separately. Endpoint decoding of derived oracle segments is not a within-call
language-switch test. Word-end/display latency is unsupported without gold word
timings. No live-call or concurrent two-channel throughput is measured.

Model weights, absolute cache/home paths and raw native stderr do not belong
here. Raw local logs remain in the ignored `.tools/` directory. Published JSON
retains public references/hypotheses, event/revision records, measured call
arrival timings and source/model/library fingerprints. Development review
commit IDs may be local-only; executed-file SHA-256 values identify the code in
the clean public snapshot.
