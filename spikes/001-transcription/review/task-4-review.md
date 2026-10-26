# Task 4 review — root guidance, repository hygiene, spike docs and public scanner

Date: 2026-10-26. Reviewer: independent task-scoped review (read-only). Scope:
[task-4-brief.md](task-4-brief.md), [preflight-resolutions.md](preflight-resolutions.md),
[task-4-report.md](task-4-report.md), the binding Global constraints in
[SPEC.md](../SPEC.md), and the Task 4-owned/authorized files as they exist in the working
tree. No ASR/native implementation, sibling runner/backend code or timed inference was
reviewed. No tests were re-run; the implementer's scanner evidence was inspected and
accepted as reported (13 test methods are present).

**Input limitation:** the referenced review package `.tools/reviews/task-4.diff` does not
exist in this checkout, and `.tools/` itself is absent. I therefore reviewed the current
files rather than the generated diff. I could not verify that commit `1605da2` contains
only the reported paths or that the working tree is byte-identical to that commit.

## Verdicts

- **Spec compliance: CONDITIONAL PASS — not publishable as-is.** The assigned artifacts
  exist, the approved IDs/goals are preserved, and no runtime/full-app claim was invented.
  However, two binding public-hygiene requirements are still unmet — a reconstructable
  work identity in tracked scanner/tests (F-01), and owner-specific home/cache paths in a
  public-bound document while the scan reports clean (F-02) — and the documented Git
  identity audit is weaker than the SPEC gate (F-04). F-03 (out-of-scope edit) needs
  coordinator ratification. All fixes are localized; no redesign is required.
- **Quality: PASS WITH FIXES.** The guidance and indexes are concise, status-honest and
  link-correct; requirements preserve all 27 FR/NFR/PROC IDs and all 15 ST inventory IDs;
  the scanner is small, stdlib-only, readable and does not echo matched values. Weaknesses
  are the embedded PII literals, incomplete rule/CLI test coverage, two report
  overstatements, and a stale Spike 002 index entry.

## What was checked

- Read `AGENTS.md`, `README.md`, `spikes/README.md`, `spikes/001-transcription/README.md`,
  `docs/requirements.md`, `docs/README.md`, both dated analysis reports, `decisions/0001`,
  `review/preflight.md`, `tools/audit_public.py` and `tests/test_public_audit.py`.
- Counted the requirement inventory: FR-01..FR-16, NFR-01..NFR-09, PROC-01..PROC-02
  (27). Counted the Natively inventory: ST-01..ST-15 (15). No add/remove/renumber.
- Verified the approved goals survive: testing both cached Parakeet and Nemotron, Firefox
  as candidate only, invisibility-where-possible/disguise-otherwise, retained
  spikes/tests/findings, no measured capability claim, HackerRank browser scenario, no
  invented assistance prohibition, no interview participation.
- Verified the health/candidacy generalization in the Purpose and preflight H-09, and the
  preflight retention note (lines 5–9): the technical finding is preserved; the personal
  wording is generalized.
- Resolved relative links among the owned Markdown. Existing targets resolve, including
  `docs/decisions/0001-native-macos-and-omp-rpc.md`, both sibling `PLAN.md` files,
  `review/progress.md`, and the Spike 002 directory/README. No broken link found.
- Inspected `.gitignore` rules by pattern; I did not run `git check-ignore` (no shell in
  this review). The report's probe results are consistent with the patterns.
- Inspected scanner source and tests against the report's claims. 13 test methods exist;
  the reported 13/13 result is plausible but not re-executed here.
- Confirmed no license file was added, no full-app/runtime claim appears in the owned docs,
  and ignored caches/model weights are not presented as trackable artifacts.

## Findings

### F-01 — High — tracked scanner and tests embed the owner's work/personal identities

- **Location:** `spikes/001-transcription/tools/audit_public.py:54-55,122-128`;
  `spikes/001-transcription/tests/test_public_audit.py:154-155,164`;
  `spikes/001-transcription/review/task-4-report.md:115-121`.
- **Issue:** The scanner composes the owner's work-email domain *and* the exact
  work-email local part as string fragments. Together they reconstruct the work address
  the scanner is supposed to reject; splitting the literals defeats the scanner's own
  regex, not public disclosure. The identity tests also hardcode the owner's personal
  Gmail address. The report says no work identity or contact detail was introduced, which
  is contradicted by the tracked scanner/test source. The employer domain itself was
  explicitly required by the task ("scan for the work email domain"), but the personal
  local part and the personal address were not.
- **Fix:** Keep only the employer-domain rule (explicitly authorized), or load prohibited
  local parts/domains from an ignored local-only config (e.g. `.tools/audit-private...`)
  or environment variable; commit only synthetic test identities (`owner@example.invalid`).
  If the owner deliberately accepts publishing the employer domain, record that decision
  and remove the personal local part. Add the scanner/test source files to the human review
  checklist so future rules do not reintroduce this pattern.

### F-02 — Medium — public-bound document still contains owner home/cache paths; scanner cannot see them

- **Location:** `docs/analysis/2026-10-25-feasibility.md:29,31,86` (owner-local OMP
  executable location, Handy application-support models location, Hugging Face cache
  snapshot location); `spikes/001-transcription/tools/audit_public.py:96-112` (rules cover
  `/Users`, `/home`, temporary folders and Windows user paths, but not `~/...`, `$HOME` or
  `%USERPROFILE%`); `tests/test_public_audit.py` (no positive test for those forms).
- **Issue:** SPEC requires no absolute home/cache paths in published artifacts. Even
  granting that `~/...` is home-relative rather than absolute, these lines identify the
  owner's private installation/cache layout, and the scanner's clean result does not
  detect them. Task 4 edited this file and reported "no public-artifact findings" and "no
  absolute home/cache path introduced"; that does not establish the document is
  publishable.
- **Fix:** Generalize the prose ("installed in a user-local bin directory", "the standard
  application-support/cache locations") or redact the paths. If the `~/` form is
  intentionally allowed, document that exception explicitly and still remove the
  owner-specific locations. Add `~`, `$HOME` and `%USERPROFILE%` detection with positive
  and negative tests, then rerun the scan before staging.

### F-03 — Medium — out-of-scope edit to `docs/analysis/2026-10-25-feasibility.md`

- **Location:** task brief "File ownership" (`task-4-brief.md:7`); report "Files changed"
  row; `docs/analysis/2026-10-25-feasibility.md:7,194`.
- **Issue:** The ownership list names only the 2026-10-26 analysis file, the root/spike
  indexes, AGENTS, `.gitignore`, requirements and the report; preflight-resolutions adds
  only the privacy-only `review/preflight.md` edit. The 2026-10-25 historical report is
  outside the assigned slice. The edit is additive and substantively sensible (dated
  superseding note), but it complicates diff ownership and the report does not call it
  out as an exception.
- **Fix:** Coordinator should either ratify the edit explicitly or revert it and place the
  superseding note in the owned 2026-10-26 analysis/README. Record the resolution in the
  integration ledger.

### F-04 — Medium — documented identity audit does not enforce an expected identity

- **Location:** `AGENTS.md:76-77`; `README.md:62-63`;
  `spikes/001-transcription/README.md:138-139`;
  `spikes/001-transcription/tools/audit_public.py:280-295,339-350,368-373`.
- **Issue:** `--git-identity` flags work-domain emails, but without `--expect-email` any
  other personal or third-party identity passes with exit 0. All three public command
  blocks omit `--expect-email`. The implementer's own evidence used it, so the documented
  command is weaker than both the report and SPEC evidence gate 6 ("scan public privacy
  and all Git identities"). The three duplicated command blocks also create drift risk.
- **Fix:** Make `--git-identity` require at least one `--expect-email` (exit 2 if absent),
  or add a `--require-expected-identity` flag and document it in one canonical command
  block referenced by the other documents. Add a temporary-repository CLI test covering an
  unexpected author, an unexpected committer and the expected personal identity.

### F-05 — Medium — test coverage and two report claims overstate what is proven

- **Location:** `spikes/001-transcription/tests/test_public_audit.py` (entire file);
  `review/task-4-report.md:40-43,76-82`.
- **Issue:** The report says tests cover "private home/temporary paths" and that the
  work-identity rule "is covered by a temporary-repository test." In fact there is no
  test for `private_temporary_path` or `windows_private_path`; there is no CLI
  `--git-identity` test and no test of `git_identity_entries`/`git log` parsing; the
  identity test constructs `Identity` objects directly. Several rules
  (`google_api_key`, `slack_token`, `provider_secret_key`, `credential_assignment`,
  `calendar_event_id`) have no test. Human output is not tested for non-echoing (only
  JSON). This weakens the privacy gate and makes the report inaccurate.
- **Fix:** Add table-driven positive and clean-negative tests for every rule; a temporary
  repository test that runs `--git-identity --expect-email` against real author/committer
  metadata including a mismatch; an unborn/no-commit case; and a human-output
  non-echoing assertion. Correct the report wording to match the tests actually present.

### F-06 — Low — Spike 002 index is stale after Task 5

- **Location:** `spikes/README.md:9` ("README pending in that directory");
  `docs/README.md:24` (planned/in progress, directory link); `README.md:23` (directory
  link). `spikes/002-hackerrank-claims/README.md` now exists and is a completed
  public-source trace.
- **Issue:** The public indexes still describe Spike 002 as having no README and as merely
  planned/in progress. The claim trace's actual status — research complete, no runtime or
  receiver-pixel evidence — is not surfaced from the index.
- **Fix:** Link `002-hackerrank-claims/README.md` from all three indexes and update the
  status to "research complete; no runtime/receiver evidence." Keep the 003/004
  planned/not-validated wording unchanged.

### F-07 — Low — scan evidence is heuristic and the recorded counts do not match integration state

- **Location:** `review/task-4-report.md:60-74,84-94`; `review/progress.md:61`.
- **Issue:** "scanned N file(s); no findings; exit 0" is presented as public-artifact
  evidence although the scanner skips ignored files, binary files and files over 4 MiB,
  and (per F-02) misses whole path forms. The report records 45 files while the ledger
  records 49 after integration; no exact file list or retained scan log exists. The report
  does label the scanner heuristic, but the conclusion should not be treated as a privacy
  audit.
- **Fix:** Record the exact command, working directory, file count/list and skipped
  classes in the final report; rerun after all staging decisions. Keep the human audit as
  the publication gate, not the scanner exit code.

### F-08 — Low — the task-specific review diff was not available

- **Location:** `.tools/reviews/task-4.diff` (absent).
- **Issue:** PLAN requires a generated task-specific diff package for review. Its absence
  prevents verification of commit scope, byte equality to `1605da2`, and whether any
  unreported file changed.
- **Fix:** Coordinator should regenerate the ignored diff artifact (or provide
  `git show --stat 1605da2`) and re-run the scoped diff review. This is a process gap, not
  a defect in the authored files.

### F-09 — Low — RED evidence is an import failure, not a behavioral red

- **Location:** `review/task-4-report.md:31-38`;
  `spikes/001-transcription/tests/test_public_audit.py:20-23`.
- **Issue:** Before the scanner existed, the test failed at import with
  `FileNotFoundError`; no detection assertion was ever observed failing. That is
  acceptable scaffolding but weak red/green evidence for a privacy guard. There is also no
  test that human-mode output omits the matched value.
- **Fix:** Record a behavioral red (e.g. a temporary stub returning no findings, then
  assert an expected detection) or label the import failure as scaffolding rather than
  red/green proof; add the human-output assertion.

### F-10 — Low — uncurated `results/` output is not ignored

- **Location:** `.gitignore:59-62`; report "Self-review" bullet on avoiding blanket
  `results/` patterns.
- **Issue:** Uncurated run outputs remain trackable, so only explicit staging prevents an
  accidental commit. This is intentional but relies on operator discipline and is not
  probed by a check-ignore case.
- **Fix:** Either add a narrow `results/*` ignore with explicit `!results/<selected>`
  exceptions, or document the staging rule in AGENTS and add a probe showing an uncurated
  result path is ignored while a selected one is trackable. Not a publication blocker by
  itself.

## Preservation review — approved IDs and goals versus private disclosures

- **IDs:** 27 requirement IDs remain exactly FR-01..FR-16, NFR-01..NFR-09,
  PROC-01..PROC-02; ST-01..ST-15 remain intact. No silent renumbering or deletion.
- **Goals:** both cached models approved for testing, Firefox candidate only,
  invisibility/disguise direction, retained spikes/tests/findings, and "no measured
  capability yet" are all present in requirements, both analysis reports, the spike README
  and the indexes. HackerRank browser scenario retained; no assistance prohibition
  invented; no interview participation.
- **Privacy:** the Purpose is generalized while preserving the functional purpose
  (retrieve/organize/express knowledge under pressure). Preflight H-09 now states the
  publication issue generically and carries a retention note; the technical finding
  (doc-level privacy audit is separate from result/path/Git scanning) is preserved.
  No private invitation ID, calendar event ID, contact detail or session description was
  found in the owned prose documents. Residual scenario-level mention of the HackerRank
  reference interview is the approved product scenario, not a candidacy detail.
- **Remaining privacy risks:** F-01 (work/personal identity literals in tracked source) and
  F-02 (home/cache paths in a public document). These must be fixed before the public
  push; the scanner's exit 0 is not sufficient.
- **License:** no license file or license choice was added; the docs correctly leave the
  choice to the owner.

## Unresolved cross-task / integration checks

1. **Full test discovery.** The report's full run had 38 tests with one `policy` import
   error. `spikes/001-transcription/policy.py` now exists, but the full suite was not
   re-run in this review. Coordinator must run
   `python3 -m unittest discover -s spikes/001-transcription/tests -v` after integration.
2. **Runner/CLI.** `run.py` is still absent; README examples are correctly labelled
   provisional. `build_engine.py` and `fetch_fixtures.py` `--help` and real invocation were
   not verified by Task 4.
3. **Spike 002 integration.** Its README now exists; indexes must be updated (F-06). Task 5
   findings are not linked from `spikes/README.md`.
4. **Spikes 003/004.** Their runtime/build/capture/focus/stealth cases remain unrun; the
   owned docs correctly say planned/in progress, not validated. No Task 4 claim depends on
   them.
5. **Review package.** `.tools/reviews/task-4.diff` is missing; regenerate for a true diff
   review (F-08).
6. **Publication gate.** Before any push, fix F-01/F-02, re-audit every Git identity with
   `--expect-email`, and review `review/progress.md:41` (personal author email) and the
   historical analysis paths. Those files are outside this slice; the coordinator owns
   the decision.
7. **Scanner rerun.** After F-01/F-02/F-04/F-05 changes, rerun both the content scan and
   the identity audit on the final staged file set and record exact counts.
8. **Report corrections.** The report's "no work identity/contact detail introduced" and
   "temporary-repository identity test" claims need correction or the underlying code/tests
   need the fixes above.

## Limitations of this review

- Read-only; no tests, Git commands, scanner runs, links fetched or inference executed.
- The absent diff package means commit-scope and byte-equality checks were not possible.
- I did not review sibling ASR/native implementations or their runtime behavior, per the
  task boundary. Findings about those are limited to the documented interfaces and the
  Task 4 report's claims.