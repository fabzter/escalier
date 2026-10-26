# Escalier

> Staircase wit, while you're still on the stairs.

Escalier is a personal, macOS-first conversation-support project. It is intended to help
with preparation before a conversation and with retrieving, organizing and expressing
relevant knowledge during a pressured or casual online conversation. It is assistive
software, not a clinical treatment, a claim of assessment success or a promise of
undetectability.

## Status

**Research with retained feasibility prototypes.** There is no full application.
Small-fixture ASR measurements exist; native UI/capture/keyboard runtime claims remain untested.

- Owner requirements and the primary shell/RPC direction are recorded in
  [docs/requirements.md](docs/requirements.md) and
  [ADR-0001](docs/decisions/0001-native-macos-and-omp-rpc.md).
- [Spike 001](spikes/001-transcription/README.md) is a retained transcription
  feasibility harness. Four cached-model batch/hybrid/native-stream arms completed
  on small licensed English/Spanish fixtures; [findings](spikes/001-transcription/FINDINGS.md)
  separate natural clips from derived assemblies and do not select a model winner.
- [Spike 002](spikes/002-hackerrank-claims/README.md) is a completed bounded public-source
  claim trace for the HackerRank reference scenario. It contains no runtime or
  receiver-pixel evidence.
- [Spike 003](spikes/003-native-shell-ui/README.md) and
  [Spike 004](spikes/004-window-capture-focus/README.md) are retained native shell/UI
  and synthetic window/focus/capture prototypes. Their headless/build/signing slices
  were independently reviewed; actual GUI and receiver-pixel matrices are NOT RUN.
- [Spike 005](spikes/005-global-keyboard-routing/README.md) is an opt-in global-shortcut
  and synthetic stealth-typing fixture, default OFF. Its headless adapter/close and
  settling-cleanup fixes passed scoped review; actual hook, browser non-delivery
  and focus evidence are NOT RUN. The [broad final integration review](spikes/001-transcription/review/final-integration-review.md)
  and [scoped documentation re-review](spikes/001-transcription/review/final-fix-review.md)
  are complete; [final headless verification](spikes/001-transcription/review/final-validation.md)
  retains the test and signature evidence. Publication uses the separate
  [public-tree/history gate](spikes/001-transcription/review/publication-plan.md).

No model choice, latency/accuracy threshold, stealth result, license or full-app
implementation is approved by this README.

## What is being investigated

The requirements cover preparation/source management, two-source local transcription,
grounded retrieval, streamed assistance with screenshots, keyboard-first operation,
privacy in browser screen sharing, and a locally buildable macOS `.app`. The current
primary direction is SwiftUI content with an AppKit coordinator, using OMP over RPC as
the agent backend. Those are directions and research questions, not finished features.

Evidence in this repository is labelled. Documentation, source inspection, local
observation, owner decisions and runtime tests are different kinds of proof. See
[the documentation index](docs/README.md) and [the spike index](spikes/README.md).

## Repository layout

```text
docs/       requirements, dated research, ADR and evidence conventions
spikes/     retained, bounded research harnesses and plans
```

Build/source/model caches, worktrees, agent state and Python/editor caches are ignored.
Small licensed fixtures, tests and selected documented results are intentionally
trackable.

## Tests and public-artifact checks

The canonical test-discovery, content-scan and expected-identity audit commands are in
[AGENTS.md](AGENTS.md#verification-commands). They are documented entry points, not
evidence that the harness has run successfully. The scanner is a heuristic guard, not a
privacy audit; command results and limitations belong in the spike review records.

## Privacy and license

Publication is gated on a privacy and Git-identity review of the intended public tree/history.
Do not add credentials, private personal details, invitation/calendar/contact content,
work identities, model weights or absolute home/cache paths. No open-source license has
been selected; that choice belongs to the owner.
