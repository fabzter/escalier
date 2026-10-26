# Escalier research spikes

Spikes are retained, bounded investigations. They are not product implementation
approval, and a spike plan or build is not a runtime result.

| Spike | Bounded question | Status | Evidence entry point |
| --- | --- | --- | --- |
| [001 — transcription](001-transcription/README.md) | Can cached Parakeet batch/hybrid decoding and genuine Nemotron native streaming produce useful bilingual partials on small fixtures? | Four real-model arms measured; final review and scoped documentation re-review complete | [Findings](001-transcription/FINDINGS.md), [execution](001-transcription/results/EXECUTION.md), [review](001-transcription/review/final-fix-review.md) |
| [002 — Natively/HackerRank claims](002-hackerrank-claims/README.md) | Which HackerRank-specific stealth claims are supported by public documentation and pinned reference source? | Research complete; no runtime or receiver-pixel evidence | [README](002-hackerrank-claims/README.md) |
| [003 — native shell and UI](003-native-shell-ui/README.md) | Can a low-fidelity SwiftUI + AppKit shell demonstrate the required panel and keyboard behavior with synthetic data? | Headless/build/signing slice reviewed; GUI NOT RUN | [Findings](003-native-shell-ui/FINDINGS.md) |
| [004 — window, focus and capture](004-window-capture-focus/README.md) | What do synthetic local browser/native fixtures show about receiver pixels, focus and window policy? | Headless/build/signing slice reviewed; runtime matrix NOT RUN | [Findings](004-window-capture-focus/FINDINGS.md) |
| [005 — global keyboard routing](005-global-keyboard-routing/README.md) | Can selected global shortcuts and explicit synthetic typing be consumed without bubbling into an inert local browser page? | Headless adapter/close/settling fixes reviewed; actual hook/recipient evidence NOT RUN | [Findings](005-global-keyboard-routing/FINDINGS.md) |

Status words here are deliberately weaker than “works” or “pass”:

- **planned** — a reviewed plan exists, but implementation may not have started.
- **in progress** — code/tests may exist; no independent integrated result is claimed.
- **NOT TESTED / NOT RUN** — no recorded runtime observation establishes the behavior.
- **retained** — the artifacts are kept for review, not deleted as scratch work.

## Rules for every spike

- Keep the question, scope, prerequisites, contracts, commands, evidence and limitations
  in the spike's own directory. Do not rewrite a plan or another worker's report.
- Preserve small licensed fixtures, tests, selected results and reviewed findings.
  Ignored caches (`.cache/`, `.tools/`, `.build/`) and model weights stay out of Git.
- Label fake/simulated clocks and synthetic content separately from real observations.
  Missing measurements are null/unsupported, not zero.
- No private data, credentials, work identities, invitation/calendar/contact details,
  weights or absolute home/cache paths in public artifacts.
- Do not copy Natively implementation code. Source inspection is reference evidence, not
  Escalier capability.
- A synthetic local test does not prove undisclosed third-party behavior or universal
  invisibility.
- No spike may silently select a production model, license, stealth policy, assistance
  policy or acceptance threshold.
