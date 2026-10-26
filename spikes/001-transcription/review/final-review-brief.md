# Final retained-spike integration review brief

Status: **TASK GATES COMPLETE; broad final integration review and scoped
documentation re-review complete.** The frozen inputs, findings and dispositions
are retained in `final-integration-review.md`, `final-fix-report.md` and
`final-fix-review.md`; fresh headless evidence is in `final-validation.md`.
This brief is not a product/runtime verdict or the public-history audit.

## Authority and deliverable

- Spike 001 `SPEC.md`, `PLAN.md`, `review/preflight-resolutions.md`, and
  `review/progress.md`: retained, bounded ASR feasibility harness with both
  existing models, licensed fixtures, actual measurements or precise measured
  blockers, and reproducible findings. No full-app design or acceptance
  threshold is approved.
- Spike 003 `PLAN.md`, `review/preflight-resolutions.md`, and `review/progress.md`:
  synthetic native shell/UI only, with independently reviewed local ad-hoc
  packaging. No launch or runtime capture/shortcut proof.
- Spike 004 `PLAN.md`, `FINDINGS.md` and its reviewed implementation: synthetic
  window/capture/focus harness, with interactive evidence gates kept explicit.
- Spike 005 `PLAN.md` and `review/preflight-resolutions.md`: the sole opt-in global
  keyboard exception, default OFF, bounded synthetic recipient test. Native
  automatic authority is foreground-application PID; page/tab/field focus and
  visibility are manual INVALID + immediate Stop conditions. Same-PID automatic
  field-focus enforcement is NOT IMPLEMENTED, and must not be implied.
- Root requirements/research and Spike 002 claim trace: distinguish owner
  observations, marketing, static source evidence and actual runtime evidence.
  Do not infer undisclosed HackerRank server-side invisibility or a universal
  Firefox workaround.
- `review/publication-plan.md`: the old development ancestry must stay local.
  Publication is the final audited tree as a new parentless public root, without
  rewriting/deleting the retained development branch. Review IDs can therefore
  be local-only; executed-file fingerprints carry measurement reproducibility.

## Existing task gates and deferred findings

Read the original and scoped review files below. This index is not permission
to silently discard a minor. Triage every residual: fix now or explicitly retain
with a reason. Do not repeat the individual task reviews from scratch where
there is no integration concern.

| Slice | Review records | Residual attention |
|---|---|---|
| Engine | `task-1-review.md`, `task-1-fix-1-review.md`, `task-1-fix-2-review.md` | Loader cache and all original R-items; unasserted finished/batch-after-snapshot variants; report-path accuracy. Terminal non-final lifecycle N-01 has a scoped PASS. |
| Runner | `task-2-review.md`, `task-2-fix-1-review.md` | One-sample replay-origin bias (0.0625 ms), explicit large-file split deferral, R=3 limitation wording, absent native-decode assertion. Preserve accepted/applied/default distinction and fatal/empty-flush behavior. |
| Fixtures | `task-3-review.md`, `task-3-fix-1-review.md` | Conversion example and historical test-count wording; license/change notices and source/derived split. |
| Guidance/privacy | `task-4-review.md`, `task-4-fix-1-review.md` | Entire retained minor list; scanner is heuristic, current-tree PASS does not sanitize private ancestors. |
| Claims | `task-5-review.md`, `task-5-fix-1-review.md` | Entire minor list, including manifest anchor coverage versus MV3/permission lines. |
| Native shell | `../../003-native-shell-ui/review/implementation-review.md`, `../../003-native-shell-ui/review/signing-review.md` | Seven original plus two signing-guard/detail notes; runtime remains NOT RUN. |
| Capture/focus | `../../004-window-capture-focus/review/implementation-review.md`, `../../004-window-capture-focus/review/fix-1-review.md` | P6..P11 plus four follow-up minor notes; retain source/artifact fingerprints and control/treatment validity boundaries. |
| Global keyboard | `../../005-global-keyboard-routing/review/implementation-review.md`, `../../005-global-keyboard-routing/review/fix-1-review.md`, `../../005-global-keyboard-routing/review/fix-2-review.md` | All unchanged minor notes; early/unsynchronized teardown-completion and close race, first-test-only adapter RED log, separate-recorder publish-order assertion; callback mapping/budget and native Unicode truncation limits; exact foreground-PID-only focus/close scope and all interactive NOT RUN rows. Round 2 addresses settling-phase `.off` cleanup; check its scoped verdict rather than treating the fix commit alone as approval. |

Worker implementation reports accompany the reviews. Counts are snapshots of
the executed revision, not promises that every earlier report equals the final
suite count.

## Integration questions

1. Do commands, links, exports, manifest consumers, language hints and effective
   streaming context agree across artifacts and findings?
2. Do retained real measurements execute committed/byte-identical code, identify
   actual loaded backend and keep warmup separate? Are natural-only conclusions
   separated from derived repetition/synthetic language switching? Endpoint
   oracle-segment decoding is not within-call bilingual proof.
3. Are raw final, committed and tentative hypotheses/revisions retained without
   mislabelling native policy units as runner word-level LA-2? Are missing native
   timings null, and word-end/display latency explicitly unsupported?
4. Is the R=3 streaming versus documented/default offline R=13 lookahead confound
   visible? Is any runtime blocker retained instead of silently falling back?
5. Are all GUI, capture-exclusion, no-bubble, focus, TCC identity/reuse and real
   browser/server-side claims still limited to the evidence actually obtained?
   Ad-hoc signing is not notarization, a Gatekeeper guarantee or stable TCC
   identity. The computer-use helper's denied permissions are not Escalier TCC
   evidence.
6. Does the prospective public tree contain only approved source, docs, licensed
   tiny fixtures and curated results—no weights/builds/caches/private paths or
   session state? Does publication preserve the exact reviewed tree and exclude
   every private development ancestor?

## Review method and output

Use the requesting-code-review reviewer template. Review read-only, with no
subagents, implementation/test changes, index/ref/checkout changes, live model
load, GUI, browser/server, tap or permission action. Write only the named review
report supplied by the coordinator. Existing covering test evidence is provided;
run only a novel, bounded probe for a concrete unanswered concern, coordinating
first if measurements are still active.

Return strengths; specific file/line Critical, Important and Minor findings;
explicit spec-compliance and quality verdicts; disposition of deferred items;
and readiness for the approved retained-spike public snapshot, not readiness of
a finished product. Any final fix wave is one consolidated worker followed by
one scoped re-review; residuals must be adjudicated, not silently dropped.
