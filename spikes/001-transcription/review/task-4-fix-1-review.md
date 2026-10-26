# Task 4 fix round 1 review — scoped re-review

Date: 2026-10-26. Reviewer: independent task-scoped re-review (read-only except for this
file). Scope: findings F-01 through F-10 of
[task-4-review.md](task-4-review.md), the fix range
`288b64bdb587d8a644944e714ad8bb626963cf6b..f758f34f4bdcf1ccb15fb495d06423fc8db9678a`
(`spikes/001-transcription/.tools/reviews/task-4-fix-1.diff`, 1502 lines), and new
breakage introduced by that fix only. Inputs also included
[task-4-brief.md](task-4-brief.md), [preflight-resolutions.md](preflight-resolutions.md)
and the fix/evidence/history sections of [task-4-report.md](task-4-report.md).

This is not a fresh review. Sibling ASR/native code, timed inference, GUI/capture
permissions and the final publication decision remain out of scope. The coordinator's
whole-tree scan finding for an unrelated sibling report is outside this fix diff and is
not re-reported here.

## Verdicts

- **Spec compliance (current tree): PASS for the fix scope.** All ten findings are
  addressed in the fix diff, and the binding public-hygiene requirements that failed in
  round 1 no longer fail in the reviewed tree. This is **not** approval to publish the
  existing history: the old private fragments remain in reachable, unpublished blob
  `1605da2`, as the report states; that is a separate coordinator publication/history
  gate.
- **Quality: PASS.** The fix is small, stdlib-only, readable and behaves as documented.
  The scanner now supports configurable rules, the `~/`/`$HOME`/`%USERPROFILE%` forms,
  expected-identity enforcement and exact scanned-path output. Tests are behavioural
  against real temporary Git repositories and use only reserved synthetic identities.

## Per-finding verdicts

### F-01 — ADDRESSED

- The reconstructable work local part and the owner's personal address are gone from the
  scanner, tests and report. A token check over all 12 changed files at `f758f34` found
  no personal local part and no full personal address; the only remaining default
  identity rule is the task-required employer-domain rule, assembled so it does not
  self-match. Tests use reserved synthetic identities (`corp.example`,
  `example.invalid`) and the scanner API/CLI accepts `--forbid-domain`/`--forbid-email`.
- The report's corrected wording matches the source: employer domain only, no individual
  local part or personal address. `--forbid-email` also gives a local-only path for
  private audits without committing the value.
- Residual: the pre-fix blob at `1605da2` still contains the old fragments. The report
  states this accurately and did not rewrite refs; a push of the current history would
  still publish them. This is the coordinator's publication gate, not a current-tree
  defect. The self-scan test prevents rule-literal self-matches but does not by itself
  stop a future arbitrary personal-address literal; the AGENTS public-hygiene rule and
  human review remain the backstop, and no dedicated scanner-source checklist line was
  added.

### F-02 — ADDRESSED

- `docs/analysis/2026-10-25-feasibility.md` now generalizes the executable, Handy model
  directory and Hugging Face cache locations ("user-local bin directory", "standard
  application-support/cache locations", "exact path omitted"). No owner-specific home or
  cache path remains in that document.
- The scanner has new `private_home_relative_path` and `private_home_env_path` rules for
  the tilde-slash, home-variable and Windows-profile path forms; positive tests exist,
  and the clean-negative case confirms generic `~/...` documentation and the
  ignore-directory names (`.omp/`, `.cache/`, `.tools/`) do not fail. A targeted scan of
  the historical report, preflight, fix report and retained review returned 0 findings,
  and the generic `/Users`/`/home`/`$HOME` list in `preflight.md:534` does not match
  because no path continuation follows.
- Residual: `$HOME/<generic-path>` documentation is intentionally treated as private
  (conservative); there is no clean-negative test for that exact syntax. No current
  tracked document triggers it.

### F-03 — ADDRESSED

- The historical-report edit was explicitly authorized in the coordinator ledger
  (historical-doc privacy scope); the report records it as a coordinator-authorized
  scope extension. No revert is required. The edit is additive history preservation plus
  path generalization, not a rewrite of the historical conclusion.

### F-04 — ADDRESSED

- `--require-expected-identity` exits 2 unless `--git-identity` and at least one
  `--expect-email` are supplied. The canonical command is documented once in
  `AGENTS.md#verification-commands`; `README.md` and the spike README link to it instead
  of duplicating the identity command. No public command block still documents a bare
  `--git-identity`.
- Real Git CLI tests cover: expected author/committer (exit 0), unexpected author,
  unexpected committer, forbidden domain, forbidden exact address, missing expected email
  (exit 2) and the unborn repository. Human and JSON output do not echo the matched
  content value.
- Residual: the gate is opt-in (`--require-expected-identity`) rather than the default
  for every `--git-identity` invocation; the canonical documented invocation is gated.
  The unborn-repository path depends on the English Git error text (`does not have any
  commits yet` / `your current branch`) rather than an exit-code or
  `rev-parse --verify` probe, so a localized Git could turn that case into an audit
  error; it passes in this environment.

### F-05 — ADDRESSED

- 26 scanner tests are present (13 before the fix). All 18 rule categories have positive
  coverage: home/`~/`/env/temp/Windows paths, signed URL, AWS/GitHub/Google/Slack/
  provider keys, private-key block, bearer token, credential assignment, invitation
  link, calendar event ID, work domain, forbidden exact address. Binary skip, explicit
  untracked input, `--include-untracked`, JSON/human non-echo, real `git log` parsing,
  expected/unexpected author and committer, forbidden domain/address and the unborn
  repository are covered. `git_identity_entries` is exercised through the CLI rather
  than only through constructed `Identity` objects.
- The report's previous overstatements ("private home/temporary paths" and "temporary-
  repository test") are corrected to match the tests actually present.

### F-06 — ADDRESSED

- Spike 002 is linked through its completed `README.md` and labelled "research complete;
  no runtime/receiver-pixel evidence" in `README.md`, `docs/README.md` and
  `spikes/README.md`. Spike 005 is indexed as in progress with runtime hook/recipient
  evidence NOT RUN, and Spikes 003/004 retain planned/not-validated wording.
- Checked at `f758f34`: the 002/003/004 targets are tracked. The three new Spike 005
  links were pending its then-untracked sibling directory; Spike 005 has since been
  committed at `77903f6`, so the links resolve in the integrated tree. This was a
  permitted pending-sibling link, not a defect.

### F-07 — ADDRESSED

- The report now records the exact command, working directory, timestamp, count (167),
  scope (tracked plus non-ignored untracked), and skipped classes (ignored, binary,
  >4 MiB). The scanner's `--json` output now carries the exact `scanned_paths` array.
  The heuristic disclaimer and the human-audit gate are explicit.
- Residual: the historical path list was not frozen or pasted, so the 167-file set is
  reproducible by rerun rather than preserved verbatim; sibling changes make any frozen
  list stale by design. The identity evidence's 134 tracked files predates the 135-file
  tree at `f758f34` (the retained review was untracked at audit time); this is a
  pre-commit snapshot, not a mismatch in the recorded result. The scanner remains a
  heuristic guard, not a privacy audit.

### F-08 — ADDRESSED

- `spikes/001-transcription/.tools/reviews/task-4.diff` exists at the spike-local ignored
  path (2601 lines, 194860 bytes), exactly as the report says; the fix diff is also
  present at 1502 lines. The earlier scout root-path assumption is explained. The old
  review copy retains its historical input limitation, and the report correctly labels
  that as accurate for the copy it was given rather than a current fact.

### F-09 — ADDRESSED

- The original import failure is explicitly relabelled "scaffolding, not a behavioral
  red", and the report refuses to invent a retroactive behavioural red. The requested
  human-output non-echoing assertion now exists in
  `test_human_output_never_echoes_the_matched_value`, in addition to the JSON
  non-echoing test. No claim depends on an unobserved red.

### F-10 — ADDRESSED (documented control)

- No blanket `results/` ignore was added, preserving curated trackability. `AGENTS.md`
  and the `.gitignore` comment now state the rule explicitly: stage selected result
  paths, never `git add -A` to sweep uncurated output, and keep uncurated scratch in
  `scratch/`. Independent `git check-ignore` probes confirm the uncurated result path
  remains trackable while selected paths are trackable — the documented intentional
  policy — and the ordinary ignore probes still pass.
- Residual: this remains operator discipline, not an enforced ignore. The finding's
  alternative narrow-ignore/blocked-uncurated probe was not implemented; the report
  states that limitation plainly. Non-blocking for the reasons F-10 already recorded.

## New breakage in the fix diff

None important. I found no case where the fix weakens a binding requirement, removes a
previous test or rule, or introduces a false public claim.

Minor observations, none requiring another fix round:

- At `f758f34` the three new Spike 005 index links pointed at a sibling directory that
  was not yet in the commit tree; Spike 005 is committed at `77903f6`, so the integrated
  tree resolves them. Only worth remembering if the publication set is ever reconstructed
  at `f758f34` alone.
- The history-evidence sentence "the only reachable commit touching the affected
  scanner/test paths is `1605da2`" is imprecise: `f758f34` also touches them. The
  substantive claim — the old fragments are reachable only in the pre-fix blob — is
  accurate for the historical table.
- `review/progress.md` continues to hold the owner's pre-existing personal Git identity
  line. It is outside this diff, was already called out in the round-1 publication gate,
  and is not a regression of F-01. The coordinator's expected-identity/publication
  decision covers it.
- Test portability is slightly narrower than the label "portable": temporary-repository
  tests assume English Git messages for the unborn case and do not force
  `commit.gpgsign=false`. They pass here and are not a spec failure.
- The report's non-echo claim is precise for content findings. The identity audit
  intentionally lists audited author/committer names and addresses in JSON and human
  mode, including a forbidden one, so "never echoes the matched value" should not be
  read as covering identity listings; no identity non-echo test exists (by design).

## Publication/history note

The fix behaves correctly for the current tree, but **this review is not approval to
push the existing history**. Commit `1605da2` is reachable from the current branch and
contains the old work-local-part/personal-address fragments; the report documents that
without rewriting refs. The coordinator must choose a clean-publication or history-
rewrite strategy before any public push. The current-tree scanner exit 0 is not a
substitute for that decision.

## What I checked

- Read the full fix diff, both scanner versions, both test versions, the fix report,
  the retained review, the root/spike indexes, `AGENTS.md`, `README.md` and `.gitignore`.
- Confirmed the fix range and files: 12 files, 928 insertions, 186 deletions; no SPEC,
  PLAN, progress ledger, fixture, runner or backend file is in the fix range.
- Verified the claimed 181-test fix snapshot from a pristine `git archive f758f34`:
  `Ran 181 tests in 2.320s — OK` (report: 2.168s; timing variance only). This includes
  the 26 scanner tests.
- Verified 26 scanner test methods, including every rule category and the real Git CLI /
  non-echo cases; no pre-fix test was deleted.
- Ran the fixed scanner over the historical report, preflight, fix report and retained
  review: `scanned 4 file(s)`, no findings, exit 0.
- Searched all changed files and the `f758f34` tree for the old personal/work fragments:
  none in changed files; the full personal address survives only in the pre-existing
  `review/progress.md` line, and the full work address/local part appears nowhere.
- Confirmed the fix diff and `task-4.diff` artifacts exist at the spike-local ignored
  path with the reported sizes; confirmed `1605da2` is reachable and that `f758f34` is a
  normal descendant (no refs rewritten).
- Checked `.gitignore` probes independently: `.omp/`, `.cache/`, `.tools/`, `.build/`,
  worktrees, Python caches, `scratch/`, `*.log` and `DerivedData/` are ignored;
  `results/run.json`, an uncurated `results/*.json`, the WAV fixture and the scanner/
  test sources are trackable.
- Resolved every relative link in the changed Markdown at `f758f34`; all targets are
  tracked except the then-pending Spike 005 plan, now committed at `77903f6`.
- Confirmed the fix files are unchanged between `f758f34` and current HEAD `77903f6`
  (only sibling 003/005 files were added).

## Limitations

- Read-only except this review file; no network fetches, GUI/capture actions, timed
  inference or commits.
- I did not re-run the current integrated full suite after later sibling commits; I
  verified the exact `f758f34` snapshot the report claims instead. Sibling code and the
  coordinator's unrelated whole-tree disclosure are out of scope.
- I could not independently verify the "byte-identical session-scratch copy" claim for
  `review/task-4-review.md` because the scratch source is not in this checkout; the
  reviewed copy itself contains no literal work/personal address.
