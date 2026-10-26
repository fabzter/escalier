# Spike 001 — measured transcription findings

Date: 2026-10-26. **Four real-model arms completed; no production model or
acceptance threshold selected.** These are feasibility observations on two
short natural recordings and two derived assemblies, not a leaderboard or a
live-call/two-channel test. The owner's separate Handy observation remains in
[OWNER-OBSERVATIONS.md](OWNER-OBSERVATIONS.md); this probe neither reproduces nor
refutes natural mid-sentence bilingual behavior in Handy.

## Execution and evidence

- Apple M2 Pro, 32 GiB RAM, macOS 27.0.1 arm64; CPython 3.13.0; four threads.
- Pinned `transcribe.cpp` `8facde6fcd8fb9caa585a5788ab450df6e8ec7db`, native/binding
  0.4.1, cached Q8_0 models. No microphone, call, LLM, model download or host
  installation was used.
- Each arm used a fresh process and one persistent loaded model. Per arm: one
  warmup pass over all four fixtures, then two measured repetitions of each.
  All **48 trials succeeded: 16 warmups and 32 measured trials**. Warmups are
  excluded from aggregates. Sequential launcher wall time was 356.85 seconds.
- All four loaded models reported **`MTL0`, Apple M2 Pro, Metal GPU**, through
  native `Model.backend` + `Model.device`, not merely a build flag. This does not
  mean every operation ran on the GPU or isolate pure GPU compute time.
- Builds finished before measurements. This was a shared workstation, not an
  isolated performance lab; a reviewer also reported a short backend-fake test
  run during the overall measurement window. Background load was not controlled.
- All result JSON parsed strictly, all trial statuses were `ok`, expected
  model/library hashes matched, and recorded runner/backend/policy/metrics/lock/
  manifest-tool source hashes matched current committed bytes after execution.
  `dirty_tracked:true` reflects coordinator documentation edits, not uncommitted
  ASR implementation. See [results/EXECUTION.md](results/EXECUTION.md).

## Final WER: natural clips first

WER v1 uses NFC/casefold, punctuation-to-spaces and whitespace collapse;
accents/ñ remain and numbers are not expanded. It is not vendor-normalized WER.
The English reference has 16 normalized tokens and Spanish 9. Natural micro-WER
therefore covers **50 reference tokens across four measured trials per arm**,
not 50 independent words/speakers. Both repeats gave the same final text/WER.

| Arm | Natural English final WER | Natural Spanish final WER | Natural micro-WER |
|---|---:|---:|---:|
| Parakeet endpoint | 0/16 = 0% | 0/9 = 0% | 0/50 = 0% |
| Parakeet hybrid, 500 ms / runner LA-2 | 0/16 = 0% | 0/9 = 0% | 0/50 = 0% |
| Nemotron endpoint | 0/16 = 0% | 0/9 = 0% | 0/50 = 0% |
| Nemotron native-stream, 1120 ms / requested R=3 | 8/16 = 50% | 1/9 = 11.11% | 18/50 = 36% |

Zero errors on two short recordings is not evidence of general bilingual
accuracy. Native R=3's English error breakdown was 3 substitutions + 5 deletions
per trial; Spanish had 1 substitution. Do not extrapolate the ranking.

## Derived fixtures are separate evidence

The repeated English clip is 2× the same 4.320 s recording. The mixed clip is
English then Spanish from **different recordings/speakers**, not natural
mid-sentence switching. See [fixture provenance](fixtures/README.md).

| Arm | Repeated English final WER, per trial | Synthetic EN→ES final WER, per trial | Derived-only micro-WER, both repeats |
|---|---:|---:|---:|
| Parakeet endpoint | 0/32 = 0% | 0/25 = 0% | 0/114 = 0% |
| Parakeet hybrid | 0/32 = 0% | 17/25 = 68% | 34/114 = 29.82% |
| Nemotron endpoint | 0/32 = 0% | 0/25 = 0% | 0/114 = 0% |
| Nemotron native-stream R=3 | 8/32 = 25% | 16/25 = 64% | 48/114 = 42.11% |

**Endpoint arms decode derived clips per oracle segment**, so their zero switch
WER is not within-call bilingual success. Hybrid and native-stream receive the
assembled clip continuously. Parakeet hybrid's switch final text contained a
Spanish-like rendering of the English part; native R=3's final switch text
retained only the Spanish sentence. Those observations warrant a controlled
follow-up; they do not identify whether language prompting, lookahead, model,
engine or policy behavior caused the errors.

The JSON's default mixed-fixture micro-WER is 20.73% for Parakeet hybrid and
40.24% for Nemotron native R=3; those aggregates mix natural and reused derived
material and are deliberately not the headline.

## Observed arrival timings, not word/display latency

Values below are **means of two measured repeats**, milliseconds. First partial
and first stable are relative to the first fixture sample's arrival; final tail
is final return minus oracle audio-end arrival. No gold word timings or actual
rendering were measured. Endpoint arms emit no partial/stable prefix, so those
metrics are unsupported/null, not zero.

| Arm / natural clip | First nonempty partial | First stable text | Final tail after audio end |
|---|---:|---:|---:|
| Parakeet endpoint / English | — | — | 149.8 |
| Parakeet endpoint / Spanish | — | — | 203.0 |
| Parakeet hybrid / English | 578.2 | 1620.6 | 186.7 |
| Parakeet hybrid / Spanish | 1649.9 | 2150.6 | 200.3 |
| Nemotron endpoint / English | — | — | 225.3 |
| Nemotron endpoint / Spanish | — | — | 248.2 |
| Nemotron native R=3 / English | 2449.2 | 2449.2 | 207.9 |
| Nemotron native R=3 / Spanish | 2438.0 | 2438.0 | 140.4 |

These are clip-specific arrival observations with n=2, not percentiles or a
near-live guarantee. Hybrid's first token can be wrong or revise later. Its
English stable text omitted the final word (stable WER 6.25%) even though final
WER was zero. For the mixed clip, hybrid stable WER was 36% while final WER was
68%; the authoritative final decode can disagree with append-only stable
history. Both views and conflicts/corrections remain in the raw JSON. Native
commit units are not assumed to equal the runner's word-level LA-2 units.

Constructor wall/native reported load times (ms), respectively: Parakeet
endpoint 176.083/34.659; hybrid 86.866/31.450; Nemotron endpoint
129.375/68.186; native-stream 91.645/37.859. These are separate fresh-process
observations, not matched cold-cache benchmarks. Calls include validation,
transport and native work. Native-stream decode-component timings remained
unknown/null for every call; batch timings were not reused.

## Context, prompting and remaining limits

- Native R=3 was requested and reported applied on every trial: native stream
  begin accepted the cache-aware value. The accepted `(left,right)` pair and
  actual model-default right context were **not exposed**. Requested/applied
  values are not a claim of an independently measured receptive field.
- Runner labels `offline_batch_R=13` refer to the documented offline setting,
  **not an observed/configured batch readback**. Its `native_default...:3` is
  the harness/binding default, not a native model-default observation. R=3
  streaming versus documented R=13 offline confounds lookahead and architecture;
  this experiment does not isolate either cause or establish that R=13 native
  streaming would behave the same way.
- Natural hints are `en-US` / `es-US`; the source Spanish locale remains
  `es_419`. The assembled mixed fixture uses `auto`. Per-call resolution and
  detected-language metadata are retained; no natural within-sentence
  code-switch fixture was tested.
- Oracle file/assembly endpoints are not VAD. Long-call rollover, live capture,
  simultaneous two-channel throughput, speaker separation, rendered display
  latency and general-world accuracy remain untested/unsupported.
- GUI launch, screen-share exclusion, focus preservation, global-key
  suppression, browser non-delivery, TCC identity/reuse and third-party
  server-side invisibility are outside this ASR evidence. Other retained
  spikes' runtime matrices remain NOT RUN.

## Interpretation, not a product decision

The batch baseline, growing-prefix hybrid and genuine native-stream paths all
ran reproducibly. Parakeet hybrid provided earlier nonempty natural-clip partials
in this configuration; final native R=3 and continuous synthetic-switch results
show important accuracy limitations. A useful next proposal is a controlled
right-context/language-prompt study with more independent natural bilingual
speech and gold word timing. No model winner, acceptance threshold or approved
full-app design follows from these tiny measurements.
