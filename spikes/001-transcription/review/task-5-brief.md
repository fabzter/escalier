# Task 5 — Natively/HackerRank claim trace

Read this first; it is your requirements. Binding scope: [SPEC.md](../SPEC.md), Global constraints. Source inventory: [existing research](../../../docs/analysis/2026-10-26-live-asr-and-browser-privacy.md), section 5. Do not redo the whole 15-row audit or read the whole implementation plan. No agents, commits, interview access, GUI actions or inference.

## File ownership

Only `spikes/002-hackerrank-claims/**` plus `spikes/001-transcription/review/task-5-report.md`. Main owns root/index/integration; other workers own ASR. Author via write/edit tools. Small downloads of public evidence are okay project-contained, no host install or private data.

## Research question

What features/evidence actually support Natively's claim to be stealth on HackerRank? Distinguish (a) generic window capture exclusion/nonactivation/focus and input behavior, (b) identity disguise/quieting, (c) genuinely platform-specific implementation, (d) marketing or unverified claim. Trace public claims to pinned source and explicit limitations, not an assurance to defeat undisclosed signals.

## Evidence already established — build on it

Natively main `b9287ec2f24bf0ea5250625286f97248052055e9`; released v2.9.2 `b439c1f07f6d2d77cbca64fc0533765bd19fe7f7`. Main reverted shipped build aliases; process_name.rs is not wired in main. Existing research maps ST-01..ST-15. User wants invisible where demonstrably possible, disguised where not; no implementation/test in Escalier yet. Natively and Handy source inspection already authorized. Public docs/search first; relevant pinned Natively source is allowed if needed. No other unapproved dependency source reads.

HackerRank official browser matrix: Firefox fully supported Legacy, unsupported New; Chrome/Edge supported both. Modern Firefox has native macOS screen sharing; non-Chromium is not proof of legacy capture or invisibility. Selected-window and full-display tests differ. The private invitation/redirect does not identify the configured experience; do not access it.

## Deliverable/validation

Retain `spikes/002-hackerrank-claims/README.md` with bounded question/method, dated and pinned sources, claim-to-mechanism/evidence/limitation table, invisible-vs-disguised classification, any genuinely HackerRank-specific finding (including honest absence), and proposed synthetic capture/focus matrix. Cite exact revisions/path/line evidence where practical; no code copying. Public claim/source observations are not receiver-pixel/server-side proof. No additional product exclusion or assistance prohibition.

Write task-5-report.md with status, files changed, exact public source checks/findings, unresolved evidence and self-review. Return brief status/findings only. Do not publish, spawn agents or imply runtime testing.
