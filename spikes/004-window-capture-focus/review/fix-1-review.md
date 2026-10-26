# Spike 004 — fix round 1 re-review (scoped)

Date: 2026-10-26. Review basis: original review at `288b64b`, fix head `0b69d2c`, path-scoped diff `81aa9e4..0b69d2c`. Runtime remains **NOT RUN**.

## Finding Verdicts

- **P1 — receiver-evidence gate accepts missing `bytesReceived` and timestamp** — **ADDRESSED**.
  Swift `ReceiverTransportReadback` now carries `timestamp: Double?` (`Sources/CapturePolicy/Evidence.swift:35-60`), and the gate at `:146-171` requires `bytesReceived > 0` and a finite `timestamp > 0` before it will consider decoded frames or dimensions. Missing, zero, negative or non-finite values return `.noReceiverEvidence` with an explicit reason (`:155-159`). JavaScript `buildReceiverEvidence` now requires positive, finite `bytesReceived` and `timestamp` before decoded frames/dimensions (`web/receiver-core.mjs:118-121,146-150`); `extractInboundVideoStats` already carried `timestamp` (`:31-43`) and `receiver.mjs:55-67` now displays it. Regression tests cover the defect in both runtimes: `Tests/CapturePolicyTests/EvidenceTests.swift:69-93` (nil/0/−1 bytes; nil/0/−1/NaN/Infinity timestamp) and `web/tests/receiver-core.test.mjs:165-203`. The previously green partial-stats case now yields **NO RECEIVER EVIDENCE**, so the gate is fail-closed in both paths.

- **P2 — treatment-occluded/control-visible can be interpreted as treatment absence** — **ADDRESSED**.
  `Sources/CapturePolicy/Evidence.swift:127-132` enters `.occluded` when an occlusion reason is recorded and **either** marker is not positively visible: `input.treatmentVisible != true || input.controlVisible != true`. The treatment-false/control-true case can no longer fall through to `.transportObserved` or emit the “absence is one local observation” reason. `Tests/CapturePolicyTests/EvidenceTests.swift:95-104` covers exactly that case and asserts both `.occluded` and the absence-interpretation reason is absent; the existing both-occluded test remains green. This matches `FINDINGS.md:118-124`. There is no JS occlusion classifier, so no JS-side change is required.

- **P3 — bundle signing/identity misreported** — **ADDRESSED**, with one residual documentation nit.
  `tools/build-app.sh:20-21` now runs exactly the owner-approved `codesign --force --sign - --timestamp=none "$APP"` then `codesign --verify --strict --verbose=2 "$APP"` under `set -euo pipefail` (`:2`); `:24` reports ad-hoc signed/verified, not Developer ID/notarized, not launched. The report records the historical nuance (`review/implementation-report.md:33,112-114`), the signing addendum (`:247-328`) and the current artifact (`:451-459`); `README.md:41-47,197-199` and `FINDINGS.md:34,251-255` describe the current ad-hoc state and the absence of Developer ID/notarization/TCC stability. My read-only checks of the rebuilt bundle match the report exactly: `Identifier=test.escalier.spike004.fixture`, `Signature=adhoc`, `CodeDirectory v=20400 size=2295 flags=0x2(adhoc) hashes=65+3`, `CDHash=e00cf564c5989c07e85125537d82c4ed454181b3`, `TeamIdentifier=not set`, `Total signatures=1`; `codesign --verify --strict --verbose=2` exits 0 with `valid on disk` / `satisfies its Designated Requirement`; executable is 1,055,648 bytes, SHA-256 `e84ee23e1713754fb8db71bd963313f1a9939654deee24c67f5ddcf3c8f27246`. No certificate, Keychain, trust, Gatekeeper, TCC, quarantine or `--deep` change is present. Residual: `review/implementation-report.md:222` still says “The pre-signing bundle was unsigned”, which is the old imprecision P3 flagged and contradicts the more accurate `:33,112-114` wording; rewrite it as “no explicit bundle signature; the executable may have carried a linker ad-hoc signature.” This does not misdescribe the current artifact.

- **P4 — report overclaims the native readback schema** — **ADDRESSED** (incidental doc fix).
  `review/implementation-report.md:138-145` now separates native policy/readback fields from the manual `FINDINGS.md` template / `EvidenceSchema.requiredManualFields` fields. No “all preflight schema fields” claim remains.

- **P5 — source-tree fingerprint recipe not reproducible** — **ADDRESSED** (incidental doc fix).
  The report now gives the exact recipe at `review/implementation-report.md:397-424`: scoped directories plus `Package.swift`, sorted relative path, UTF-8 path + NUL + file bytes + NUL, SHA-256. I ran that recipe read-only from the spike directory: current tree, 48 files → `2508c55909280e82f4ae22220745593adc9e4f57a161d50194a868a2acbc2e00`, exactly the report. I also applied the same recipe to the `288b64b` tree via `git ls-tree`/`git show` (read-only): 47 files → `f7a974ceaf9e41db49b32991f64206fd18c23d136907252bf2accf41bd08635f`, exactly the retained historical value. Both current and historical 47-file values are now reproducible.

## New Breakage in the Fix Diff

None at Critical or Important severity. The delta (`81aa9e4..0b69d2c`, path-scoped; 13 files, +826/−71) is confined to `Evidence.swift`, its tests/fixtures, `receiver-core.mjs`, `receiver.mjs`, the receiver tests, `web-audit.mjs`, `build-app.sh`, the signing test, the README/FINDINGS/report documentation, and the added original-review record. No P6–P11 code, runtime claim, external/audio/server behavior, app launch, capture or permission path was added.

The new signing test genuinely checks failure propagation: `tools/tests/build-app-signing.test.mjs:40-45` pins both exact commands and rejects `--deep`; `:47-57` runs a fake `codesign` that exits 42 on the signing call and requires a nonzero build plus the stub’s stderr; `:59-69` makes the stub exit 43 only for `--verify` and requires a nonzero build plus that stderr. With `set -euo pipefail` in the script, neither signing nor verification failure can be silently converted into a green build. The tests use only OS-temp scratch/bundle paths.

## Spec Verdict

**Spec compliance: PASS for the fix round.** P1 and P2 now satisfy the binding preflight evidence rules: missing/zero/non-finite inbound bytes or timestamp cannot produce receiver-transport evidence, and a treatment-occluded/control-visible cell cannot be used to interpret treatment absence. P3’s current artifact is correctly described as ad-hoc signed and strict-verified, with no Developer ID signature/notarization and no stable TCC identity; the code-signing identifier is recorded as an identity surface. P4/P5 evidence documentation is corrected and P5’s recipe reproduces exactly. No runtime, stealth or privacy claim was added; the runtime matrix remains **NOT RUN**.

## Quality Verdict

**Quality: PASS with minor residuals.** The fix is minimal and targeted; the Swift and JS gates are both fail-closed; tests cover the exact missing-field and partial-occlusion defects; the signing-failure paths are exercised with real subprocess behavior; and the fingerprint recipe is reproducible. The remaining items are documentation/evidence hygiene, not code defects.

**Fix round: all findings addressed; no new Critical/Important breakage.**

## Residual Minors

- `review/implementation-report.md:222` — stale “pre-signing bundle was unsigned” sentence; conflicts with the corrected `:33,112-114` account. Reword to the explicit/linker-signature distinction (P3 residual).
- `README.md:107-108` — the receiver bullet names `framesDecoded > 0` plus frame/video dimensions but omits `bytesReceived`/`timestamp`; the detailed oracle at `:143-148` and the code are correct. Update the summary for operator consistency.
- `review/implementation-report.md:315-316` — the signing-pass 48-file hash `27e54adb…` refers to an uncommitted intermediate tree. Unlike the current 48-file value and the historical 47-file value, it cannot be reproduced from a commit; label it as an unreproduced signing-pass snapshot or tie it to the tree/commit used.
- `tools/web-audit.mjs:370-380` — the new `/timestamp/` check is a literal presence tripwire, not a semantic gate; the actual fail-closed guarantee is unit-tested. Acceptable as a static guard, but it should not be cited as evidence by itself.

## Out-of-Scope Observations

- P6–P11 remain deferred exactly as the report states (`review/implementation-report.md:464-465`); the fix diff does not touch those areas and this review gives them no verdict. In particular, P7 (connection-failure stale evidence) remains open: the new timestamp requirement proves a timestamp was recorded, not that it is fresh.
- `web/receiver-core.mjs:122-130` still accepts `Infinity` for `framesDecoded` and frame dimensions (`typeof number && > 0`) while bytes and timestamp are finite-checked. Real `RTCPeerConnection.getStats()` values are finite; this is pre-existing, not introduced by this fix, and non-blocking.
- Runtime remains **NOT RUN**: no receiver pixels, focus/blur/visibility, click-through, occlusion, activation-policy, browser-compatibility, TCC/identity or stealth result exists. A native flag or build pass is not receiver evidence.

## Checks and Basis

- Basis: original review at `288b64b`; fix head `0b69d2c`; diff `spikes/001-transcription/.tools/reviews/window-capture-fix-1.diff` (`81aa9e4..0b69d2c`, path-scoped). Inputs read: `PLAN.md`, `review/implementation-review.md`, `review/implementation-report.md` (signing addendum + fix round), `spikes/003-native-shell-ui/review/preflight-resolutions.md`.
- Accepted coordinator/worker evidence, not re-run: `tools/run-tests.sh` 54 Swift / 80 Node tests all PASS; web audit 12 files PASS; native audit 14 files PASS; static validation PASS; rebuilt real bundle codesign strict-verified, ad-hoc, `TeamIdentifier=not set`, identifier `test.escalier.spike004.fixture`, binary SHA-256 `e84ee2…` matching the report.
- Independent read-only checks I ran: `codesign -dv --verbose=4` and `codesign --verify --strict --verbose=2` on the current bundle; `shasum -a 256` and `stat` on the executable; the P5 Python recipe over the current 48-file tree and over the `288b64b` 47-file tree. No suite was re-run. No app, browser, server or capture was launched; no permission prompt or TCC state was touched; no code edit, subagent, staging, index or commit occurred. This review file is the only write.
