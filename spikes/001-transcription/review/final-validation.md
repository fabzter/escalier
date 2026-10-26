# Final retained-spike headless verification

Date: 2026-10-26. Coordinator execution record at local development commit
`54450511648a9c3dd9a12f47f1b5c0f4b657ee93`. This is test/artifact evidence,
not a review verdict, public-history audit or product/runtime acceptance.

## Executed target and scope

The working tree and index had no tracked differences before or after this
verification. Imports of `run`, `backend`, `metrics` and `policy` resolved to
this repository's `spikes/001-transcription/` files. Before committing the
documentation fixes, 24 source/blob/size/SHA-256 comparisons across the four
curated JSON files matched the recorded executed bytes and committed blobs.
The six recorded source artifacts, raw result JSON, engine lock, fixture
manifest, audio/references, tools and tests were not changed by that fix wave.

No real-model experiment was rerun. The retained 48 successful trials remain
the measurements described in [EXECUTION](../results/EXECUTION.md); this final
headless verification does not relabel them as new runs.

## Fresh command results

All commands below exited 0. Python commands ran from the repository root;
other commands ran from the named spike directory. Logs were generated under
the ignored `spikes/001-transcription/.tools/reviews/final-*.log` paths, not
staged as public artifacts. `PYTHONDONTWRITEBYTECODE=1` was set.

| Slice | Command | Fresh result |
|---|---|---|
| 001 ASR | `python3 -m unittest discover -s spikes/001-transcription/tests -v` | 204 tests, 2.180 s, OK |
| 001 engine | `python3 spikes/001-transcription/tools/build_engine.py --verify-only` | Locked source/library verification passed; engine 0.4.1 |
| 001 fixtures | `python3 spikes/001-transcription/tools/fetch_fixtures.py --verify-only` | 4 fixtures, 914,576 WAV/reference bytes, 28.560 s |
| 003 shell | `swift test` | 36 XCTest cases, 0 failures |
| 004 capture policy | `xcrun swift test --scratch-path .build` | 54 XCTest cases, 0 failures |
| 004 browser/tools | `node --test web/tests/*.test.mjs tools/tests/*.test.mjs` | 80 tests, 80 pass, 0 fail |
| 004 static validation | `node tools/validate.mjs` | Web audit 12 files; native audit 14 files; PASS; no app/browser/server/capture started |
| 005 keyboard | `swift test` | 69 core + 15 adapter XCTest cases, 0 failures |
| 005 browser/tools | `node --test tools/tests/*.test.mjs` | 12 tests, 12 pass, 0 fail |

Total: **470 test cases** (204 Python + 174 Swift + 92 Node), with no test
failures. Repeated XCTest suite-summary lines are not counted twice. Static,
fixture, engine and signature checks are additional checks, not extra cases
in that total.

## Existing packaged artifacts: fresh strict readback

Each retained local bundle was checked with `codesign --verify --strict
--verbose=2`, `codesign --display --verbose=4`, `plutil -lint` on its Info.plist,
and SHA-256 of its main executable. All three were valid on disk, satisfied
their Designated Requirement and had a valid plist. Each reported
`Signature=adhoc` and `TeamIdentifier=not set`. These are readbacks of the
previously built/signed bundles; this final matrix did not launch them.

| Spike / bundle | Identifier | CDHash | Executable SHA-256 |
|---|---|---|---|
| 003 / `.build/EscalierShell.app` | `local.escalier.spike003.shell` | `e63022c72f75dc376d5df719247dbf3aaf8441de` | `246da4b70ff69d03caba72440f7316d5847f287de5e3378400f561e2687161d2` |
| 004 / `.build/EscalierCaptureFixture.app` | `test.escalier.spike004.fixture` | `e00cf564c5989c07e85125537d82c4ed454181b3` | `e84ee23e1713754fb8db71bd963313f1a9939654deee24c67f5ddcf3c8f27246` |
| 005 / `.build/RoutingFixture.app` | `local.escalier.spike005.keyboard` | `1b49aea7cb5d1c576b06302eded608bc5899792e` | `db1c37a22f32186b6107ed6ff1f4b11df0098e2388bec92f4e5d6ed8a8fc1dc1` |

No certificate, Keychain trust, Gatekeeper, quarantine, TCC or permission
state was changed. Ad-hoc verification is not notarization, Developer ID,
launchability assurance or stable TCC grant reuse.

## Documentation/data checks and boundaries

The coordinator independently recomputed all 24 cells of the eight-row
natural-clip arrival-timing table from strict per-trial JSON: all matched.
The former Spanish hybrid first-stable value `2105.1` was rejected by an
in-memory negative control; the correct mean is `2150.616`, displayed as
`2150.6` ms. Four paired WAV/reference files total 914,576 bytes; adding the
5,515-byte manifest gives 920,091 bytes. The attribution NOTICE is separately
retained and is not part of that WAV/reference/manifest subtotal.

At the documentation-fix checkpoint, 70 Markdown files had zero missing
relative-link targets; the heuristic public-artifact scanner checked 207
candidate files with no findings. Those are checkpoint counts, not a claim
that they describe later review/validation artifacts or public reachability.

GUI rendering/launch, receiver pixels, capture exclusion, focus/non-theft,
actual event-tap suppression, browser no-bubble behavior, permission identity
and reuse, and undisclosed HackerRank server-side behavior remain **NOT RUN /
NOT ESTABLISHED**. Same-PID page/tab/field focus remains a manual INVALID +
immediate Stop condition, not native automatic enforcement. No model winner,
acceptance threshold, license, assistance policy or full-app design is chosen.

The remaining public-history/identity gates are defined in
[the publication plan](publication-plan.md). A clean working-tree scan and
these tests do not sanitize the retained private development ancestry.
