# Preflight resolutions and dispatch amendments

2026-10-26. Read with your task brief. Current SPEC.md is authoritative over older brief wording. The preflight's three pre-dispatch blockers are resolved in SPEC.md. Implementation-time issues below are acceptance checks, not reasons to redesign the approved scope.

## All workers

- User also authorized parallel native shell/UI and synthetic stealth spikes. Separate directories `003-native-shell-ui/` and `004-window-capture-focus/`; no cross-editing. Task 4 should link these as planned/in progress, not validated. No GUI/capture permissions or interview actions are authorized automatically.
- `.gitignore` now exists before cache creation. Task 4 may refine it but preserve curated fixture/results trackability. Stage/commit remains coordinator-only.
- Root discovery command remains `python3 -m unittest discover -s spikes/001-transcription/tests -v`; tests add spike root to sys.path. No hypothesis that discover automatically does so.
- Python 3.13.0, M2 Pro/32 GiB/macOS27.0.1. Both expected cached models were verified by SHA and size in progress.md; no need to rediscover private directories. Workers do not read private files or run timed inference.

## Task 1 — binding contract

SPEC now supports `library_path`, per-call language, caller `feed_chunk_ms` versus native `att_context_right_frames`, native stable-prefix/agreement_n, cumulative full_text, committed/tentative/final fields, nullable native decode time distinct from call wall time, and explicit feed/final/lifecycle rules. Prefer official stdlib-only Python binding loaded from the pinned local checkout; no pip install or new custom helper unless concretely necessary. Source lock records vendored ggml UPSTREAM/patches/tree, not nonexistent submodules. Bindings/struct initializers and pointer-copy safety require review. Record runtime backend via engine API. No implicit build/network on Engine construction. Preserve the raw authoritative final text and unknown timings as null.

## Task 2 — replay and metrics

Follow new API exactly. Frozen selected tick/audio horizon before each call; coalesce missed partials after slow decode and prioritize final. Native chunks never drop audio. Per-fixture language prompt (`asr_language`) without reloading model. Record native committed text separately from runner word-level LA-2. Defined normalizer, empty-reference WER, micro-aggregation, real/fake timing fields, strict atomic JSON and collision checks in SPEC. Max-window path rejects, and tests prove rejection; do not implement long-call rollover in this spike. Native R=3 versus offline R=13 is an explicit context confound, not an architecture-isolated accuracy comparison.

## Task 3 — fixture acquisition

FLEURS rows API was checked and fails scan limits; do not repeat it or download whole splits. Use verified bounded HTTP Range prefix + direct TSV/filename mapping strategy in SPEC, pinned revision, selecting short complete WAV members. Require HTTP206/content-range; never silently fetch full tar. Complete source.config/locale/item_id/audio_sha256/reference_column/asr_language/conversion provenance. Default <=20 sec clips; optional longer clips must not be in default run. No audioop on Python3.13. Include CC-BY-4.0 attribution and offline corrupt-copy/path/schema tests.

## Task 4 — public hygiene and additional ownership

Generalize personal health/candidacy details in public research prose; preserve the functional purpose and initial HackerRank product scenario. No extra owner confirmation is required for public target already approved, but no private diagnosis or invitation/calendar/contact content should be exposed. Raw preflight report includes the old sensitive wording: sanitize those quotes while preserving the technical findings, adding a note that public prose was generalized. You may edit `review/preflight.md` for this privacy-only purpose.

Also own `spikes/001-transcription/tools/audit_public.py` and `tests/test_public_audit.py`: small stdlib public-artifact scanner with red/green tests. Scan candidate/tracked text for private absolute paths, signed URL credentials, work email domain, secrets, unintended private identifiers; don't false-fail mere documentation of .omp or literal regex definitions. Support untracked reviewed file input before first commit and Git author/committer identity audit. Test scanner rejects representative private data in temp files. Report all changes. Root/spike indexes should distinguish build-ready from interactively tested.

## Task 5 — claims

Existing inventory is authoritative prior research; focus on HackerRank-specific support versus generic mechanisms. No new scope/policy debate. Reference the forthcoming independent synthetic capture/focus spike rather than claiming it has run.
