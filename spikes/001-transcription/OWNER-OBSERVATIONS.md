# Owner observations — transcription

2026-10-26, reported directly by the owner during spike implementation.

> Nemotron Streaming 3.5 through Handy works in English and Spanish, including switching between the two languages mid-sentence, and feels reasonably fast / near real time.

Classification: **OWNER-OBSERVED**, not an independently reproduced Escalier benchmark. Model files/size/SHA-256 were independently checked; Handy app/backend/build/stream settings, exact utterances, latency and accuracy were not measured by this harness. Do not discard this observation because the harness is not yet complete, and do not relabel it as harness-measured evidence.

Implications for this spike:

- Nemotron is already a locally demonstrated bilingual streaming candidate, not merely a model-card hypothesis.
- Preserve per-call language selection and explicitly test the automatic/no-fixed-language path where the engine supports it.
- Include a small public-fixture-derived bilingual sequence with an honest reference and provenance. A concatenation of separate English/Spanish recordings is a **synthetic assembled switch**, potentially across different speakers; it does not independently reproduce natural within-sentence code-switching.
- Retain the distinction between subjective Handy responsiveness, harness call/queue timings and live-call/display latency. No production model selection or numerical acceptance threshold is inferred.
