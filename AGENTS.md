# AGENTS — Escalier

Escalier is a personal, macOS-first conversation-support project. It is in a
research/spike phase: there is no full application, no selected licence, and no
measured capture/focus/stealth result. Spike 001 does have four measured ASR arms
on small licensed fixtures — see
[findings](spikes/001-transcription/FINDINGS.md) and
[execution](spikes/001-transcription/results/EXECUTION.md).

## Read first

- [Requirements baseline](docs/requirements.md) — stable FR/NFR/PROC IDs, owner
  decisions, proposals, observations and research amendments. Do not renumber or
  silently rewrite owner-approved requirements.
- [ADR-0001](docs/decisions/0001-native-macos-and-omp-rpc.md) — owner-approved primary
  direction, subject to feasibility.
- [Spikes index](spikes/README.md) — what is implemented, planned, tested or merely a
  proposal.
- The dated [research reports](docs/README.md) — evidence and hypotheses, not runtime
  results.

## Approved direction, not completed app

- SwiftUI content with an AppKit window/application coordinator is the primary shell.
- OMP is the agent/LLM backend, integrated over RPC.
- Per-conversation model/tool/skill configuration, retained/deletable results and
  canonical source text outside OMP history are requirements.
- ASR runtime, capture path, retrieval design, persistence details, keyboard bindings,
  identities and licence remain open.
- Do not turn a proposal, spike plan, build flag or green unit test into a product
  capability, runtime result or model-selection decision.

## Evidence and claims

Use the labels defined in `docs/requirements.md`: OWNER-RESOLVED, OWNER-OBSERVED,
DOCUMENTED, SOURCE-OBSERVED, LOCALLY-OBSERVED, PROPOSED and NOT TESTED.

- Preserve commands, versions, conditions, source/model/fixture fingerprints and
  limitations when recording a result.
- Fake/simulated clocks or fixtures must stay distinguishable from measured timing.
- Missing metrics are `null`/unsupported with an explanation, never fabricated zeroes.
- Word-end/display latency and undisclosed third-party side effects are not inferred
  from local flags, sender previews, source comments or model-card claims.
- A build succeeding is not a UI pass; a unit test passing is not receiver-pixel,
  focus, capture or latency evidence.

## Research and dependency rules

- Read official documentation/help before dependency source. Inspect pinned
  implementation only when documentation is insufficient and the task/owner authorizes
  it.
- Do not copy Natively implementation code. Reference mechanisms and reimplement
  independently.
- Do not install host-wide packages, download new models, use a microphone, join a live
  call/interview, run LLM inference, or trigger GUI/capture/permission prompts without
  explicit task scope.
- Use project-local ignored `.cache/`, `.tools/` and `.build/` for sources, downloads
  and builds. Never commit model weights.
- Retain spikes, tests, plans and reviewed findings in their own directories. Do not
  delete reviewed artifacts or replace a finding with an unrecorded retry.

## Public repository hygiene

- Never publish credentials, secrets, signed URLs, work identities, private
  invitation/calendar/contact content, model weights or absolute home/cache paths.
  Documentation that merely names ignored directories such as `.omp/`, `.cache/` or
  `.tools/` is fine.
- Keep small licensed fixtures, tests and selected documented results trackable. There is
  intentionally no blanket `results/` ignore: stage selected result paths explicitly and
  never use `git add -A` to sweep uncurated run output into a commit.
- No licence choice is delegated to an agent.
- Stage explicit paths. Do not force push, publish a release/version bump, or create a
  public remote unless the coordinator's assignment explicitly says so.

## Verification commands

From the repository root:

```bash
python3 -m unittest discover -s spikes/001-transcription/tests -v
python3 spikes/001-transcription/tools/audit_public.py --include-untracked
python3 spikes/001-transcription/tools/audit_public.py --git-identity \
  --require-expected-identity --expect-email "<your-public-git-email>"
```

The test discovery command requires the spike's tests to exist and adds the spike root
to `sys.path`; discovery alone does not. The identity command must be run with every
public Git identity you intend to allow; `--require-expected-identity` exits 2 if the
expected email is missing. Additional forbidden domains/addresses can be added with
`--forbid-domain`/`--forbid-email`. The default Git scan skips ignored files; all modes
skip binary files and files over 4 MiB. It is a heuristic guard, not a privacy audit. Do
not report a command as passing unless it was actually run, and do not treat a passing
scan as a substitute for human review.
