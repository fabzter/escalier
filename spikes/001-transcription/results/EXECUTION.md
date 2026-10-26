# Execution identity and reproduction record

Date: 2026-10-26. These four outputs came from direct execution of
`python3 spikes/001-transcription/run.py`, not module-name/PYTHONPATH selection
or an unverified archive. Imports of `run`, `backend`, `metrics` and `policy`
resolved to this spike. Before/after checks matched executed source bytes to
committed Git blobs; all recorded JSON source hashes matched after execution.

The runner recorded local development commit
`94c895b9a057e1deca57ce2832e36655120ee759`, branch `spike/transcription`, and
`dirty_tracked:true` because coordinator documentation was being updated.
ASR implementation bytes were committed and unchanged. The private development
lineage is intentionally not published: the public repository starts from the
final audited tree. Development review IDs are local audit references, not
public checkout instructions. Numerical fingerprints below identify this
execution independently of that lineage.

## Executed input fingerprints (SHA-256)

Paths below are relative to Spike 001.

| Input | SHA-256 |
|---|---|
| `run.py` | `c158b8fc9b1e22b318501a2c16cdab3a3a66609722d9113f7fa0d88924474772` |
| `backend.py` | `5038005b546b4c6bb7c175c8f7fda6a5a99ffba6047c94f5b75e32a6801d53ff` |
| `metrics.py` | `3781343cc1e9889805deac97b4e112c5f264ea70d6f718cfdad5cccd84d6cd00` |
| `policy.py` | `a28d57c177fcfdab84846e3b4e5d44d3642f543cbd91115aadcbcf15f1f89223` |
| `fixtures/manifest_tools.py` | `aa2412af16e545b98fa870c97454012b37b3bf189c299e2d383a0983ffd73ab4` |
| `fixtures/manifest.json` | `f6aa1ab5ef83b89a6643f120314ed2fc16e5754d7cbd995d7b5c955e9b933794` |
| `engine.lock.json` | `6b2aa39024eaa6f41524350a3e927e5bda457ef61ef2f97c3651822c8919c63f` |
| native `libtranscribe` 0.4.1, 1,966,072 bytes | `d3fe0516d1a0d8bcf80775857c29813ddbd787ebbe10d2bb507c2f0d0733d195` |
| Parakeet v3 Q8_0, 739,508,576 bytes | `5859f77944efcd8eafa23a6350731960b2b55b2203df51f319665c807d802cc7` |
| Nemotron 3.5 streaming Q8_0, 751,094,240 bytes | `b94545b313b3223fda7b2857a52681da813935c2127643d1e9ff0c23d988089c` |

Native engine pin:
`handy-computer/transcribe.cpp@8facde6fcd8fb9caa585a5788ab450df6e8ec7db`.
The lock/build records retain vendored ggml revision/patches and build flags.
Models and binaries are not included in Git.

## Recorded invocations

Run from the repository root, using the existing cached model files. Supply
`PARAKEET_MODEL` and `NEMOTRON_MODEL` privately; no private path is retained here.
These are the original output names. For a new run choose unused output names;
the runner intentionally refuses collisions rather than silently overwriting
this evidence.

```sh
LIBRARY=spikes/001-transcription/.tools/build/src/libtranscribe.dylib
MANIFEST=spikes/001-transcription/fixtures/manifest.json

python3 spikes/001-transcription/run.py --model "$PARAKEET_MODEL" --library "$LIBRARY" --manifest "$MANIFEST" --arm endpoint --output spikes/001-transcription/results/parakeet-endpoint.json --warmup 1 --repeats 2 --clock-mode real --threads 4
python3 spikes/001-transcription/run.py --model "$PARAKEET_MODEL" --library "$LIBRARY" --manifest "$MANIFEST" --arm hybrid --output spikes/001-transcription/results/parakeet-hybrid.json --warmup 1 --repeats 2 --clock-mode real --threads 4
python3 spikes/001-transcription/run.py --model "$NEMOTRON_MODEL" --library "$LIBRARY" --manifest "$MANIFEST" --arm endpoint --output spikes/001-transcription/results/nemotron-endpoint.json --warmup 1 --repeats 2 --clock-mode real --threads 4
python3 spikes/001-transcription/run.py --model "$NEMOTRON_MODEL" --library "$LIBRARY" --manifest "$MANIFEST" --arm native-stream --output spikes/001-transcription/results/nemotron-native-stream.json --warmup 1 --repeats 2 --clock-mode real --threads 4 --feed-chunk-ms 1120 --right-context-frames 3 --commit-policy stable-prefix --agreement-n 2
```

The four processes ran sequentially and exited 0. Warmup=1 means one pass over
four fixtures, not one fixture total. Each JSON has 12 successful trials:
4 warmups + 8 measured. Across all four: 16 warmups + 32 measured.
Native R=3 begin reported applied=3 on every trial; accepted context pair/model
default was not exposed. See findings for the documented offline-R=13 confound.

## Retained output fingerprints

| File | Bytes | SHA-256 |
|---|---:|---|
| `parakeet-endpoint.json` | 312443 | `cead9e6366e6534fa14cafb1ca958c516aad9d72f1a9ce9a6b7220727432e640` |
| `parakeet-hybrid.json` | 842073 | `fd79981447b4f381461983b808e4401eb92294c514cee9a94fde08456a30c32d` |
| `nemotron-endpoint.json` | 320698 | `41c16fba5e5bb911c7d2d52b44d2bddd71c3da70cb4e6a4ba19936616a6cc487` |
| `nemotron-native-stream.json` | 922629 | `0d8a259e232e303aec6c5dfa9a73fa5ed36c80afa3ae003e07b82e9ad551de5a` |

Validation after execution: strict JSON/nonfinite rejection; 12 `ok` statuses
per file; 8 measured and 4 warmup trials; expected model/library/source hashes;
native applied context and null native-stream decode-component values; whole
candidate-tree heuristic privacy scan. This does not replace the final Git
identity/reachable-public-history audit.

Raw native stderr remains in ignored `.tools/` logs and is not published. See
[measured findings](../FINDINGS.md) for interpretation, uncertainty and unsupported
metrics. No first-word/display latency, real-time deadline, live-call throughput,
GUI or stealth capability is established by this execution record.
