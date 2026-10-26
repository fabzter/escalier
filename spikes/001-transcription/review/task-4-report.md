# Task 4 report — root guidance, repository hygiene and spike documentation

Date: 2026-10-26. Status: **complete within the assigned ownership after fix round 1; no
commit, no publication, no measured inference and no licence choice.** The fix-round
full-suite snapshot is green (181 tests); the coordinator still must rerun it on the final
integrated tree. History and publication evidence is documented below.

## Files changed

| Path | Change |
| --- | --- |
| `.gitignore` | Refined ignore rules for `.omp/`, local dependency/build/model caches, worktrees, Python/editor caches and local logs. Kept curated WAV fixtures, tests and selected `results/` trackable. |
| `AGENTS.md` | New concise project guidance: approved native/RPC direction, docs before dependency source, evidence labels, retained spikes, public-hygiene rules, explicit staging and test commands. |
| `README.md` | New public-facing purpose/status overview. It describes assistive conversation support, not a finished app, and links the docs/spikes. |
| `spikes/README.md` | New spike index distinguishing planned, in-progress, retained and NOT TESTED work. |
| `spikes/001-transcription/README.md` | New harness README covering scope, prerequisites, backend contract, manifest, arms, metric cautions, provisional commands, tests and findings status. |
| `docs/requirements.md` | Generalized the Purpose prose to remove private personal wording; generalized calendar/session specifics; added dated research-scope amendments preserving all requirement IDs. |
| `docs/README.md` | Updated document statuses, added spike index and clarified that no full-app plan is approved while bounded spikes are authorized. |
| `docs/analysis/2026-10-26-live-asr-and-browser-privacy.md` | Added the 2026-10-26 research update, both-model approval, retained-artifact direction, superseded download/throwaway wording and links to the retained/synthetic spikes. |
| `docs/analysis/2026-10-25-feasibility.md` | Preserved the historical snapshot and added the 2026-10-26 update that supersedes the then-open probe/download state; generalized owner-specific executable/cache paths under the coordinator-authorized scope extension. |
| `spikes/001-transcription/review/preflight.md` | Privacy-only generalization of personal-risk wording in the publication finding and verdict; added a retention note. Technical findings unchanged. |
| `spikes/001-transcription/tools/audit_public.py` | New stdlib public-artifact and Git-identity scanner, refined in fix round 1: configurable forbidden domains/addresses, `~/`/`$HOME`/`%USERPROFILE%` path rules, expected-identity enforcement and exact scanned-path JSON. |
| `spikes/001-transcription/tests/test_public_audit.py` | New tests for every rule category, synthetic-only identities, untracked input, real Git CLI identity audit and non-echoing JSON/human output. The original import-only red is preserved as scaffolding, not presented as behavioral TDD. |
| `spikes/001-transcription/review/task-4-review.md` | Byte-identical retained copy of the independent review (session-scratch source). |
| `spikes/001-transcription/review/task-4-report.md` | This report, including fix-round adjudications and history evidence. |

No SPEC, PLAN, progress ledger, fixture, runner, backend or sibling-owned file was edited.

## Checks and exact results

### Scanner red/green

1. **RED (scaffolding, not a behavioral red):** before `tools/audit_public.py` existed,
   running `python3 spikes/001-transcription/tests/test_public_audit.py -v` failed at
   import with `FileNotFoundError` for the scanner path. This is not claimed as proof
   that a detection assertion was observed failing; the fix round did not invent a
   retroactive behavioral red.
2. **GREEN (original):** after implementation, the same direct test command ran
   **13 tests: OK**.
3. **GREEN (fix round):** direct and discovery runs now report **26 tests: OK**:
   `python3 spikes/001-transcription/tests/test_public_audit.py` and
   `python3 -m unittest discover -s spikes/001-transcription/tests -p 'test_public_audit.py' -v`.
   This exercises the discovery path; the tests add the spike root to `sys.path` as
   required.

The scanner tests cover private home/temporary/Windows paths, `~/`, `$HOME` and
`%USERPROFILE%` forms, signed URLs, configurable forbidden work/exact identities,
credential shapes, invitation links, binary skipping, untracked-file input, expected
identity enforcement through real temporary-repository author/committer CLI runs, the
unborn-repository case, and both JSON and human output that never echo the matched value.
They also scan the scanner and test source themselves to prevent rule-literal
self-matches.

### Full repository test command

The original run reported **38 tests with one import error** in a then-in-progress
`test_policy`. After sibling integration, the final fix-round run is green:

```text
python3 -m unittest discover -s spikes/001-transcription/tests -v
Ran 181 tests in 2.168s
OK
```

This includes the 26 scanner tests. Sibling files are still changing; this is a snapshot,
not a guarantee for the final integrated tree.

### Public-artifact scan

Final fix-round scan, 2026-10-26T12:12:43Z, working directory repository root:

```text
python3 spikes/001-transcription/tools/audit_public.py --include-untracked --json
scanned_files: 167
findings: 0
exit: 0
```

Scope: all Git-tracked files plus non-ignored untracked files. Ignored caches, binary
files and files over 4 MiB are skipped. The exact 167-path list is the `scanned_paths`
array emitted by `--json`; it is reproducible rather than pasted because sibling slices
were still adding files, so a frozen list would immediately drift. An earlier scan
version false-positived on public static `?Expires=` values in retained source evidence;
the signed-URL rule now requires a signature/credential-shaped query key, with a
regression test. The scanner is a heuristic guard, not a complete privacy audit.

### Git identity audit

Fix-round command (the expected personal Git identity is public and authorized, but is
not reproduced in this report):

```text
python3 spikes/001-transcription/tools/audit_public.py --git-identity \
  --require-expected-identity --expect-email <public-git-email> --json
scanned_files: 134
identities: 2 (author, committer)
identity_findings: 0
exit: 0
```

This scope is tracked files only; content scanning above additionally covers non-ignored
untracked files. The audit reads author/committer metadata; it does not prove provider-side
identity retention. Temporary-repository CLI tests now cover expected identity,
unexpected author, unexpected committer, forbidden domain/address and the unborn-repository
case.

### `.gitignore` behavior

Probed with `git check-ignore -q --no-index`:

- Ignored: `.omp/state`, `.cache/download`, `.tools/src`, `.build/out`, `worktrees/w`,
  `__pycache__/x.pyc`, `.pytest_cache/x`, `scratch/uncurated`, `foo.log`,
  `DerivedData/x`.
- Trackable: `spikes/001-transcription/fixtures/clip.wav`,
  `spikes/001-transcription/results/run.json`,
  `spikes/001-transcription/tests/test_public_audit.py`,
  `spikes/001-transcription/tools/audit_public.py`.
- No blanket `results/` ignore was added: selected documented results must remain
  trackable. `AGENTS.md` and the `.gitignore` comment now require explicit result-path
  staging instead of `git add -A`; this is an operator-discipline control, not a
  scanner-enforced one.

### Documentation integrity

- Requirement inventory remains **27 IDs**: FR-01..FR-16, NFR-01..NFR-09,
  PROC-01..PROC-02. No ID was added, removed or renumbered.
- The Natively inventory remains **15 IDs**: ST-01..ST-15.
- A relative-link check over the owned Markdown resolved every existing target. Spikes
  002 and 005 are linked through their existing README/PLAN; sibling task reports are not
  linked individually. This report, the preflight link and the copied review resolve.
- `spikes/001-transcription/review/task-4-review.md` is a byte-identical copy of the
  reviewer's session-scratch markdown (`diff -q` exit 0). It has no exact work or personal
  address literal.
- `python3 spikes/001-transcription/tools/audit_public.py --help` exits successfully and
  documents Git mode, explicit paths, `--include-untracked`, `--git-identity`,
  `--require-expected-identity`, `--expect-email`, `--forbid-domain`, `--forbid-email`
  and `--json`.

## Privacy edits

- Removed private personal wording from the public Purpose while retaining the functional
  product purpose: retrieving, organizing and expressing knowledge under pressure.
- Generalized the calendar evidence: removed session-content specifics and retained only
  the corroborating HackerRank reference-scenario conclusion, the absence of an explicit
  assistance prohibition and the absence of private identifiers.
- Generalized the raw preflight publication finding and its checklist, and added a
  retention note. No technical finding was dropped.
- No private invitation identifier, calendar identifier, contact detail, individual work
  or personal address, credential, signed URL, model weight or owner-specific home/cache
  path was introduced. The built-in scanner rule retains only the employer domain
  explicitly required by the task; individual local parts and personal addresses were
  removed. Public model references use basenames only.
- No licence was selected. No assistance prohibition was invented and no interview
  participation was performed or implied.

## Fix round 1 — review dispositions

The unchanged review is retained as `review/task-4-review.md` (byte-identical session-
scratch copy; `diff -q` exit 0). It contains no exact work or personal address literal.

- **F01 — fixed.** Removed the reconstructable work-email local part and the personal
  address from the scanner/tests. Only the employer domain explicitly required by the
  task remains as a default rule; individual local parts/addresses were removed.
  `--forbid-domain`/`--forbid-email` add configurable patterns for local audits. Tests
  now use reserved `.example`/`.invalid` synthetic identities. Public Git personal
  identity is still allowed when supplied as the expected identity.
- **F02 — fixed.** Generalized the historical report's OMP executable, Handy model
  directory and Hugging Face cache locations. Added `~/`, `$HOME`/`${HOME}` and
  `%USERPROFILE%` path rules with positive tests, plus a clean-negative test for ordinary
  public email and non-private path syntax. The current tree scans clean.
- **F03 — coordinator-authorized.** The historical-report privacy/status edit is retained
  under the coordinator's explicit scope extension; it was not reverted into private
  wording. The coordinator is recording the extension in the integration ledger.
- **F04 — fixed.** Added `--require-expected-identity`, which exits 2 without at least one
  `--expect-email`. The canonical command is now documented once in `AGENTS.md`; README
  and the spike README link to it instead of duplicating command blocks. Temporary-repo
  CLI tests cover expected author/committer, unexpected author, unexpected committer,
  forbidden domain/address and the unborn-repository case.
- **F05 — fixed.** Tests now cover every rule category (home/temp/Windows/env/`~/`,
  signed URLs, work/forbidden identities, all credential shapes, invitation links,
  calendar IDs, binary skip), real Git log parsing/CLI identity failures, and both JSON
  and human non-echoing output. The original overstated claims are corrected here.
- **F06 — fixed.** Spike 002 links to its completed README and is labelled research
  complete with no runtime/receiver evidence. Spike 005 is indexed as in progress with
  runtime hook/recipient evidence NOT RUN. Spikes 003/004 keep planned/not-validated
  wording.
- **F07 — addressed.** Exact fix-round scan counts/scope/date are recorded above; the
  JSON output now lists `scanned_paths`. The scanner still skips ignored, binary and
  >4 MiB files, and remains a heuristic, not the publication gate.
- **F08 — evidence limitation recorded.** The task-specific diff actually exists at
  `spikes/001-transcription/.tools/reviews/task-4.diff` (2601 lines, 194860 bytes), not
  at the root `.tools` path the scout assumed; that directory is an ignored project-local
  view. I did not regenerate old reviews or alter the diff. The review's input limitation
  remains accurate for the copy it was given.
- **F09 — preserved, not rewritten.** The original red is retained and explicitly labelled
  scaffolding/import-only, not behavioral TDD. The human-output non-echoing assertion was
  added in this fix round and is not claimed as red-first.
- **F10 — documented control, not blanket ignore.** No broad `results/` ignore was added,
  because selected documented results must stay trackable. `AGENTS.md` and the
  `.gitignore` comment require explicit result-path staging and forbid `git add -A` to
  sweep uncurated output; this remains an operator-discipline control.

### Unpublished reachable history evidence

No refs/history were altered. The only reachable commit touching the affected scanner/test
paths is `1605da20ce6d70fdbfd34836648e8202e4265c55`:

| Path | Historical versions | Fragment counts (no literal reproduced) |
| --- | --- | --- |
| `spikes/001-transcription/tools/audit_public.py` | 1 | 1 employer-domain fragment, 1 work-local-part fragment |
| `spikes/001-transcription/tests/test_public_audit.py` | 1 | 1 employer-domain fragment, 3 personal-address token occurrences |
| `spikes/001-transcription/review/task-4-report.md` | 1 | 0 |
| `spikes/001-transcription/review/task-4-review.md` | 0 | 0 |

A constructed-token check over the current scanner, tests, report and copied review found
zero occurrences of the removed work-local-part and personal-address fragments. Because
the old blob remains in reachable unpublished history and the coordinator reports the
remote empty, a non-destructive clean-publication strategy is the coordinator's decision;
this worker did not rewrite history. The copied review/report contain no exact full work
or personal address literal.

## Deferred / integration checks

- The full discovery snapshot is green, but the coordinator must rerun it on the final
  integrated/tree-staged state; sibling files are still changing.
- `run.py`, `build_engine.py` and `fetch_fixtures.py` now exist and their `--help` exits
  were checked successfully (no model load, build, fixture fetch or inference). Real arm
  invocations remain unrun; the README keeps examples **provisional**.
- Spike 002's README now exists and is linked. Task 1/2/3/5 reports and the other spike
  reports are sibling-owned and may still change.
- Spikes 003, 004 and 005 remain plans/in-progress. Their runtime, build, capture, focus,
  hook and stealth cases are NOT TESTED. No timed inference, GUI, capture or permission
  prompt was run.
- External links in the research reports were not re-fetched; this slice amended status,
  scope and privacy wording, not the technical source inventory.

## Self-review and concerns

- I did not turn build plans, source inspection or unit tests into runtime claims. The
  ASR README explicitly says no inference is measured and no model is selected.
- The ignore rules avoid blanket `*.wav`/`results/` patterns, preserving the curated
  evidence requirement.
- The scanner is deliberately conservative about output: it reports path/line/rule only,
  never the matched value. Explicit-path mode intentionally scans reviewed files outside
  Git tracking and is the intended pre-first-commit workflow.
- The scanner defaults to the task-required employer domain but stores no individual
  work or personal address. Additional forbidden patterns are opt-in, so a local audit
  can cover private identities without committing them.
- Remaining risk: doc-level privacy and Git identity still need the coordinator's human
  audit and explicit staging. The scanner cannot inspect ignored/untracked files unless
  explicitly passed, and it does not detect every possible private identifier. The old
  unpublished commit blob must be handled by the coordinator's publication strategy.
- No blanket `results/` ignore exists; explicit staging remains required, as documented.
- Root AGENTS/README wording is project guidance, not a product-policy decision; it
  should be read with the requirements and ADR.
