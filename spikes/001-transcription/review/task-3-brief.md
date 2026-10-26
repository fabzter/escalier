# Task 3 — licensed bilingual fixtures and provenance

Read this first; it is your task requirements. Binding scope and manifest schema: [SPEC.md](../SPEC.md), Global constraints and Fixture manifest contract. Do not read the whole plan or other workers' reports. No subagents or commits. Author files with write/edit tools; execution/build/download can use shell.

## File ownership

Only `spikes/001-transcription/fixtures/**`, `tools/fetch_fixtures.py`, `tests/test_fixtures.py` and your report. Runner/backend/docs belong to other workers. Fixture WAVs/text may be committed if small and properly licensed. Do not overwrite other files.

## Implementation

- Verify a public dataset's license and pin revision/config/split/rows before downloading a few small English and Spanish recordings with human reference transcripts. Suggested discovery: google/fleurs en_us/es_419 through datasets-server per-row URLs; investigate official docs/API first. Do not download whole dataset archives, new models or private audio.
- PCM16 mono 16000 Hz WAVs and UTF-8 reference text. Use existing tools/stdlib; no host installs. Record source hash and conversion tool/version when converted, canonical dataset URL/revision/row (not transient signed URLs), derived WAV/reference hashes and duration.
- Use the exact manifest schema in SPEC.md; paths relative to spike root. Clearly mark fixture/file boundaries as oracle endpoints, not real VAD/gold word timing. Include short English+Spanish clips and, if useful, a longer explicitly derived repeated/assembled fixture without making the default run costly. Reference concatenation/provenance must be explicit, not ASR-generated.
- Document source/license/attribution/derivation/regeneration in fixtures/README.md and include required license notice. Downloads stay project-local. Fetching must not silently overwrite modified tracked fixtures; implement explicit output/verification behavior.

## TDD

Red then green offline tests of schema, safe confined paths, IDs, WAV channels/rate/sample width/duration, reference/audio hashes and oracle bounds. Corrupt a copied temporary fixture to prove integrity checks fail. Tests must not depend on network or touch actual curated fixture bytes destructively. Use unittest compatible with root discover command in SPEC.md.

## Report

Write `spikes/001-transcription/review/task-3-report.md`: status DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED; changed files; verified license/source links; exact regeneration command; total bytes/durations; exact red/green test commands/results and self-review. Return brief status/tests/concerns only. Do not run timed inference, commit, or spawn agents.
