#!/usr/bin/env python3
"""Acquire the pinned, licensed FLEURS fixture slice without whole-split downloads.

Strategy (verified against the pinned revision):

* fetch the small per-language ``test.tsv`` directly and verify its SHA-256;
* request one bounded HTTP Range prefix of ``audio/test.tar.gz`` (at most 8 MiB),
  require HTTP 206 plus ``Content-Range``, and stream-read the prefix with
  ``tarfile`` in ``r|gz`` mode;
* map tar member filenames to TSV rows (tar order is not TSV row order), accept
  only complete members, then convert the source IEEE-float WAVs to PCM16 mono
  16 kHz WAVs with the Python standard library;
* build two explicitly derived assemblies from those converted clips (a repeated
  English clip and a synthetic EN->ES switch) with concatenated references and
  derived_assembly segments;
* write outputs atomically and refuse to overwrite a curated file whose bytes
  differ unless ``--force`` is explicit.

The tool never downloads a full dataset archive or installs anything.  Source
WAVs and bounded prefixes are kept under the spike's ignored ``.cache/``.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import struct
import sys
import tarfile
import tempfile
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
sys.path.insert(0, str(FIXTURES_DIR))
import manifest_tools  # noqa: E402

REVISION = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"
USER_AGENT = "escalier-fixture-provenance/1"
MAX_PREFIX_BYTES = 8 * 1024 * 1024
MIN_PREFIX_BYTES = 4 * 1024 * 1024
MAX_TSV_BYTES = 2 * 1024 * 1024
CONVERSION_TOOL = "python3.13 stdlib float32-to-pcm16 mono/16000 v1"
DERIVED_CONVERSION_TOOL = (
    "python3.13 stdlib float32-to-pcm16 mono/16000 v1; repeat-2 pcm assembly v1"
)


class FetchError(RuntimeError):
    """A bounded acquisition, conversion, or output-write invariant failed."""


@dataclass(frozen=True)
class Source:
    config: str
    locale: str
    revision: str
    tsv_url: str
    tsv_sha256: str
    tar_url: str
    tar_bytes: int
    split: str = "test"
    license: str = "CC-BY-4.0"
    prefix_bytes: int = MAX_PREFIX_BYTES


@dataclass(frozen=True)
class Selection:
    fixture_id: str
    config: str
    row: int
    item_id: str
    language: str
    asr_language: str
    audio_sha256: str
    wav_name: str
    reference_name: str


def _hf_base(config: str) -> str:
    return (
        f"https://huggingface.co/datasets/google/fleurs/resolve/{REVISION}"
        f"/data/{config}"
    )


SOURCES = {
    "en_us": Source(
        config="en_us",
        locale="en_us",
        revision=REVISION,
        tsv_url=f"{_hf_base('en_us')}/test.tsv",
        tsv_sha256="74c046239374deeb60fa63f258f907388093a32bcaa3140965f70ef05c79f7ca",
        tar_url=f"{_hf_base('en_us')}/audio/test.tar.gz",
        tar_bytes=289851356,
    ),
    "es_419": Source(
        config="es_419",
        locale="es_419",
        revision=REVISION,
        tsv_url=f"{_hf_base('es_419')}/test.tsv",
        tsv_sha256="d107a93a4f54a18ac25cd470bb4cdadce14fb075b0c1d1542258e274d209ec09",
        tar_url=f"{_hf_base('es_419')}/audio/test.tar.gz",
        tar_bytes=582112372,
    ),
}

SELECTIONS = (
    Selection(
        fixture_id="fleurs-en-us-10233995782544396174",
        config="en_us",
        row=518,
        item_id="10233995782544396174.wav",
        language="en",
        asr_language="en-US",
        audio_sha256="bfa2f3fb72a05cbcb7c0000a460435f2d0eedca7c5cc90f01aacc89127df7f63",
        wav_name="en_us_10233995782544396174.wav",
        reference_name="en_us_10233995782544396174.txt",
    ),
    Selection(
        fixture_id="fleurs-es-419-10149016836336603986",
        config="es_419",
        row=322,
        item_id="10149016836336603986.wav",
        language="es",
        asr_language="es-US",
        audio_sha256="13b06188bd62a1a63ed350e6fe1a1ee8518db1ea7bc8f75d72849ca023de7c32",
        wav_name="es_419_10149016836336603986.wav",
        reference_name="es_419_10149016836336603986.txt",
    ),
)

DERIVED_SOURCE = next(s for s in SELECTIONS if s.language == "en")
MIXED_EN_SOURCE = next(s for s in SELECTIONS if s.language == "en")
MIXED_ES_SOURCE = next(s for s in SELECTIONS if s.language == "es")
DERIVED_FIXTURE_ID = "derived-en-us-10233995782544396174-repeat2"
DERIVED_WAV_NAME = "derived_en_us_10233995782544396174_repeat2.wav"
DERIVED_REFERENCE_NAME = "derived_en_us_10233995782544396174_repeat2.txt"
DERIVED_REPEATS = 2

MIXED_FIXTURE_ID = "derived-en-us-es-419-switch"
MIXED_WAV_NAME = "derived_en_us_es_419_switch.wav"
MIXED_REFERENCE_NAME = "derived_en_us_es_419_switch.txt"
MIXED_CONVERSION_TOOL = (
    "python3.13 stdlib float32-to-pcm16 mono/16000 v1; "
    "switch-concat v1 sources="
    f"{MIXED_EN_SOURCE.config}:{MIXED_EN_SOURCE.row}:{MIXED_EN_SOURCE.item_id}:"
    f"{MIXED_EN_SOURCE.audio_sha256};"
    f"{MIXED_ES_SOURCE.config}:{MIXED_ES_SOURCE.row}:{MIXED_ES_SOURCE.item_id}:"
    f"{MIXED_ES_SOURCE.audio_sha256} pcm v1"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_content_range(
    header: str, expected_total: int | None = None
) -> tuple[int, int, int]:
    """Parse a satisfied ``Content-Range: bytes START-END/TOTAL`` header."""
    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", (header or "").strip())
    if not match:
        raise FetchError(f"invalid Content-Range: {header!r}")
    start, end, total = (int(group) for group in match.groups())
    if start != 0:
        raise FetchError(f"bounded Range must start at byte 0, got {start}")
    if end < start or end >= total:
        raise FetchError(f"invalid Content-Range bounds: {header!r}")
    if expected_total is not None and total != expected_total:
        raise FetchError(
            f"unexpected source size: range says {total}, pinned {expected_total}"
        )
    return start, end, total


def write_if_unchanged(path: Path, data: bytes, *, force: bool = False) -> str:
    """Atomically write ``data`` unless a different existing file would be replaced."""
    path = Path(path)
    if path.exists():
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise FetchError(f"cannot inspect existing output {path}: {exc}") from exc
        if existing == data:
            return "unchanged"
        if not force:
            raise FetchError(
                f"refusing to overwrite modified file {path}; use --force or "
                "--output-dir for an explicit alternate destination"
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False
    )
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except BaseException:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise
    return "written"


def _ensure_project_local(spike_root: Path, path: Path, label: str) -> Path:
    root = spike_root.resolve(strict=True)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise FetchError(f"{label} must stay inside the project: {path}")
    return resolved


def _http_open(url: str, *, headers: dict[str, str] | None = None):
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, **(headers or {})}
    )
    return urllib.request.urlopen(request, timeout=180)


def _fetch_tsv(source: Source, cache_dir: Path) -> list[list[str]]:
    with _http_open(source.tsv_url) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise FetchError(f"unexpected TSV HTTP status {status} for {source.config}")
        data = response.read(MAX_TSV_BYTES + 1)
    if len(data) > MAX_TSV_BYTES:
        raise FetchError(f"TSV for {source.config} exceeds {MAX_TSV_BYTES} bytes")
    actual = sha256_bytes(data)
    if actual != source.tsv_sha256:
        raise FetchError(
            f"TSV sha256 mismatch for {source.config}: {actual} != pinned "
            f"{source.tsv_sha256}"
        )
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{source.config}__test.tsv"
    cache_path.write_bytes(data)
    rows = []
    for line_number, line in enumerate(data.decode("utf-8").splitlines(), 1):
        if not line:
            continue
        fields = line.split("\t")
        if len(fields) != 7:
            raise FetchError(
                f"{source.config} TSV line {line_number} has {len(fields)} fields, "
                "expected 7"
            )
        rows.append(fields)
    if not rows:
        raise FetchError(f"empty TSV for {source.config}")
    return rows


def _fetch_prefix(source: Source, cache_dir: Path, prefix_bytes: int) -> bytes:
    if not (MIN_PREFIX_BYTES <= prefix_bytes <= MAX_PREFIX_BYTES):
        raise FetchError(
            f"prefix_bytes must be between {MIN_PREFIX_BYTES} and "
            f"{MAX_PREFIX_BYTES}, got {prefix_bytes}"
        )
    end = prefix_bytes - 1
    with _http_open(source.tar_url, headers={"Range": f"bytes=0-{end}"}) as response:
        status = getattr(response, "status", 200)
        if status != 206:
            # Never read a 200 response body: that would be a whole-split fetch.
            raise FetchError(
                f"server did not honour bounded Range for {source.config} "
                f"(HTTP {status}); refusing to download the whole split"
            )
        content_range = response.headers.get("Content-Range")
        parse_content_range(content_range or "", expected_total=source.tar_bytes)
        data = response.read(prefix_bytes + 1)
    if len(data) != prefix_bytes:
        raise FetchError(
            f"expected {prefix_bytes} prefix bytes for {source.config}, got {len(data)}"
        )
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / f"{source.config}__test_prefix_{prefix_bytes}.bin").write_bytes(data)
    return data


def extract_complete_members(
    prefix: bytes, wanted_items: set[str]
) -> dict[str, bytes]:
    """Stream a truncated tar.gz prefix and return only complete wanted members."""
    remaining = set(wanted_items)
    found: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(prefix), mode="r|gz") as archive:
            for member in archive:
                if not member.isfile():
                    continue
                name = PurePosixPath(member.name).name
                if name not in remaining:
                    continue
                handle = archive.extractfile(member)
                if handle is None:
                    raise FetchError(f"cannot extract tar member {member.name}")
                data = handle.read()
                if len(data) != member.size:
                    raise FetchError(
                        f"truncated tar member {member.name}: "
                        f"{len(data)} of {member.size} bytes"
                    )
                found[name] = data
                remaining.discard(name)
                if not remaining:
                    break
    except (tarfile.ReadError, EOFError, OSError) as exc:
        if remaining:
            raise FetchError(
                "bounded tar prefix ended before all selected members were read: "
                f"{sorted(remaining)}"
            ) from exc
    if remaining:
        raise FetchError(
            f"selected members not found in bounded tar prefix: {sorted(remaining)}"
        )
    return found


def convert_float32_wav_to_pcm16(data: bytes) -> bytes:
    """Convert mono IEEE-float 16 kHz WAV bytes to PCM16 mono 16 kHz WAV bytes."""
    if len(data) < 12 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise FetchError("source audio is not a RIFF/WAVE file")
    position = 12
    fmt_chunk = None
    payload = None
    while position + 8 <= len(data):
        chunk_id = data[position:position + 4]
        size = struct.unpack("<I", data[position + 4:position + 8])[0]
        start = position + 8
        if start + size > len(data):
            raise FetchError("truncated WAV chunk")
        if chunk_id == b"fmt ":
            fmt_chunk = data[start:start + size]
        elif chunk_id == b"data":
            payload = data[start:start + size]
        position = start + size + (size & 1)
    if fmt_chunk is None or len(fmt_chunk) < 16:
        raise FetchError("source WAV has no fmt chunk")
    if payload is None:
        raise FetchError("source WAV has no data chunk")
    format_tag, channels, rate, _byte_rate, block_align, bits = struct.unpack(
        "<HHIIHH", fmt_chunk[:16]
    )
    if format_tag != 3 or channels != 1 or rate != 16000 or bits != 32:
        raise FetchError(
            "expected mono IEEE-float 32-bit 16000 Hz source, got "
            f"tag={format_tag} channels={channels} rate={rate} bits={bits}"
        )
    if block_align != 4 or len(payload) % 4:
        raise FetchError("source float payload is not aligned to 4-byte samples")
    count = len(payload) // 4
    samples = struct.unpack("<%df" % count, payload)
    pcm = bytearray(count * 2)
    for index, sample in enumerate(samples):
        if not math.isfinite(sample):
            raise FetchError("source audio contains a nonfinite sample")
        if sample > 1.0:
            sample = 1.0
        elif sample < -1.0:
            sample = -1.0
        struct.pack_into("<h", pcm, index * 2, int(round(sample * 32767.0)))
    output = io.BytesIO()
    with wave.open(output, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(bytes(pcm))
    return output.getvalue()


def _pcm16_frames(wav_bytes: bytes) -> int:
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as handle:
            if (
                handle.getnchannels() != 1
                or handle.getsampwidth() != 2
                or handle.getframerate() != 16000
                or handle.getcomptype() != "NONE"
            ):
                raise FetchError("converted WAV is not PCM16 mono 16000 Hz")
            return handle.getnframes()
    except (wave.Error, EOFError) as exc:
        raise FetchError(f"converted WAV is unreadable: {exc}") from exc


def build_fixtures(
    spike_root: Path,
    cache_dir: Path,
    prefix_bytes: int,
    relative_dir: PurePosixPath,
) -> dict[Path, bytes]:
    """Download the pinned slice, convert it, and return output bytes by path."""
    outputs: dict[Path, bytes] = {}
    source_wavs: dict[str, bytes] = {}
    references: dict[str, str] = {}

    for config in sorted({selection.config for selection in SELECTIONS}):
        source = SOURCES[config]
        rows = _fetch_tsv(source, cache_dir)
        wanted = {
            selection.item_id
            for selection in SELECTIONS
            if selection.config == config
        }
        prefix = _fetch_prefix(source, cache_dir, prefix_bytes)
        members = extract_complete_members(prefix, wanted)
        for selection in SELECTIONS:
            if selection.config != config:
                continue
            if selection.row >= len(rows):
                raise FetchError(
                    f"{config} TSV has {len(rows)} rows; selected row "
                    f"{selection.row} is missing"
                )
            row = rows[selection.row]
            if row[1] != selection.item_id:
                raise FetchError(
                    f"{config} row {selection.row} names {row[1]!r}, expected "
                    f"{selection.item_id!r}"
                )
            raw_transcription = row[3]
            if not raw_transcription.strip():
                raise FetchError(
                    f"{config} row {selection.row} has an empty raw_transcription"
                )
            source_bytes = members[selection.item_id]
            actual_source_sha = sha256_bytes(source_bytes)
            if actual_source_sha != selection.audio_sha256:
                raise FetchError(
                    f"source audio sha256 mismatch for {selection.item_id}: "
                    f"{actual_source_sha} != pinned {selection.audio_sha256}"
                )
            num_samples = int(row[5])
            cache_dir.mkdir(parents=True, exist_ok=True)
            (cache_dir / f"source__{selection.item_id}").write_bytes(source_bytes)
            converted = convert_float32_wav_to_pcm16(source_bytes)
            frames = _pcm16_frames(converted)
            if frames != num_samples:
                raise FetchError(
                    f"{selection.item_id}: converted {frames} frames but TSV says "
                    f"{num_samples}"
                )
            duration = frames / 16000
            reference_text = raw_transcription.rstrip("\r\n") + "\n"
            source_wavs[selection.fixture_id] = converted
            references[selection.fixture_id] = reference_text
            outputs[Path(selection.wav_name)] = converted
            outputs[Path(selection.reference_name)] = reference_text.encode("utf-8")

    manifest_entries = []
    for selection in SELECTIONS:
        converted = source_wavs[selection.fixture_id]
        reference_bytes = references[selection.fixture_id].encode("utf-8")
        frames = _pcm16_frames(converted)
        duration = frames / 16000
        source = SOURCES[selection.config]
        manifest_entries.append(
            {
                "id": selection.fixture_id,
                "language": selection.language,
                "asr_language": selection.asr_language,
                "wav": str(relative_dir / selection.wav_name),
                "reference": str(relative_dir / selection.reference_name),
                "wav_sha256": sha256_bytes(converted),
                "reference_sha256": sha256_bytes(reference_bytes),
                "duration_s": round(duration, 6),
                "source": {
                    "url": source.tar_url,
                    "revision": source.revision,
                    "license": source.license,
                    "config": source.config,
                    "locale": source.locale,
                    "split": source.split,
                    "row": selection.row,
                    "item_id": selection.item_id,
                    "audio_sha256": selection.audio_sha256,
                    "reference_column": "raw_transcription",
                },
                "conversion": {"tool": CONVERSION_TOOL},
                "segments": [
                    {
                        "start_s": 0.0,
                        "end_s": round(duration, 6),
                        "kind": "oracle_file_boundary",
                    }
                ],
            }
        )

    derived_source = source_wavs[DERIVED_SOURCE.fixture_id]
    derived_source_frames = _pcm16_frames(derived_source)
    derived_pcm = (
        _extract_pcm_payload(derived_source) * DERIVED_REPEATS
    )
    derived_wav = _pcm16_from_payload(derived_pcm)
    derived_frames = _pcm16_frames(derived_wav)
    if derived_frames != derived_source_frames * DERIVED_REPEATS:
        raise FetchError("derived assembly frame count is inconsistent")
    source_text = references[DERIVED_SOURCE.fixture_id].strip()
    derived_reference = (" ".join([source_text] * DERIVED_REPEATS) + "\n").encode(
        "utf-8"
    )
    outputs[Path(DERIVED_WAV_NAME)] = derived_wav
    outputs[Path(DERIVED_REFERENCE_NAME)] = derived_reference
    source_duration = derived_source_frames / 16000
    derived_duration = derived_frames / 16000
    manifest_entries.append(
        {
            "id": DERIVED_FIXTURE_ID,
            "language": DERIVED_SOURCE.language,
            "asr_language": DERIVED_SOURCE.asr_language,
            "wav": str(relative_dir / DERIVED_WAV_NAME),
            "reference": str(relative_dir / DERIVED_REFERENCE_NAME),
            "wav_sha256": sha256_bytes(derived_wav),
            "reference_sha256": sha256_bytes(derived_reference),
            "duration_s": round(derived_duration, 6),
            "source": {
                "url": SOURCES[DERIVED_SOURCE.config].tar_url,
                "revision": REVISION,
                "license": SOURCES[DERIVED_SOURCE.config].license,
                "config": DERIVED_SOURCE.config,
                "locale": SOURCES[DERIVED_SOURCE.config].locale,
                "split": SOURCES[DERIVED_SOURCE.config].split,
                "row": DERIVED_SOURCE.row,
                "item_id": DERIVED_SOURCE.item_id,
                "audio_sha256": DERIVED_SOURCE.audio_sha256,
                "reference_column": "raw_transcription",
            },
            "conversion": {"tool": DERIVED_CONVERSION_TOOL},
            "segments": [
                {
                    "start_s": 0.0,
                    "end_s": round(source_duration, 6),
                    "kind": "derived_assembly",
                },
                {
                    "start_s": round(source_duration, 6),
                    "end_s": round(derived_duration, 6),
                    "kind": "derived_assembly",
                },
            ],
        }
    )

    en_fixture = MIXED_EN_SOURCE
    es_fixture = MIXED_ES_SOURCE
    en_wav = source_wavs[en_fixture.fixture_id]
    es_wav = source_wavs[es_fixture.fixture_id]
    en_frames = _pcm16_frames(en_wav)
    es_frames = _pcm16_frames(es_wav)
    mixed_wav = _pcm16_from_payload(
        _extract_pcm_payload(en_wav) + _extract_pcm_payload(es_wav)
    )
    mixed_frames = _pcm16_frames(mixed_wav)
    if mixed_frames != en_frames + es_frames:
        raise FetchError("mixed-language assembly frame count is inconsistent")
    mixed_reference = (
        references[en_fixture.fixture_id].strip()
        + " "
        + references[es_fixture.fixture_id].strip()
        + "\n"
    ).encode("utf-8")
    outputs[Path(MIXED_WAV_NAME)] = mixed_wav
    outputs[Path(MIXED_REFERENCE_NAME)] = mixed_reference
    en_duration = en_frames / 16000
    mixed_duration = mixed_frames / 16000
    manifest_entries.append(
        {
            "id": MIXED_FIXTURE_ID,
            "language": "mixed",
            "asr_language": "auto",
            "wav": str(relative_dir / MIXED_WAV_NAME),
            "reference": str(relative_dir / MIXED_REFERENCE_NAME),
            "wav_sha256": sha256_bytes(mixed_wav),
            "reference_sha256": sha256_bytes(mixed_reference),
            "duration_s": round(mixed_duration, 6),
            "source": {
                # A singular source object cannot represent two recordings; the
                # first segment's source is recorded here and both sources are
                # documented explicitly in fixtures/README.md and the conversion
                # tool string below.
                "url": SOURCES[en_fixture.config].tar_url,
                "revision": REVISION,
                "license": SOURCES[en_fixture.config].license,
                "config": en_fixture.config,
                "locale": SOURCES[en_fixture.config].locale,
                "split": SOURCES[en_fixture.config].split,
                "row": en_fixture.row,
                "item_id": en_fixture.item_id,
                "audio_sha256": en_fixture.audio_sha256,
                "reference_column": "raw_transcription",
            },
            "conversion": {"tool": MIXED_CONVERSION_TOOL},
            "segments": [
                {
                    "start_s": 0.0,
                    "end_s": round(en_duration, 6),
                    "kind": "derived_assembly",
                },
                {
                    "start_s": round(en_duration, 6),
                    "end_s": round(mixed_duration, 6),
                    "kind": "derived_assembly",
                },
            ],
        }
    )

    manifest = {
        "schema_version": 1,
        "sample_rate": 16000,
        "fixtures": manifest_entries,
    }
    manifest_bytes = (
        json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    outputs[Path("manifest.json")] = manifest_bytes
    return outputs


def _extract_pcm_payload(wav_bytes: bytes) -> bytes:
    position = 12
    while position + 8 <= len(wav_bytes):
        chunk_id = wav_bytes[position:position + 4]
        size = struct.unpack("<I", wav_bytes[position + 4:position + 8])[0]
        start = position + 8
        if chunk_id == b"data":
            return wav_bytes[start:start + size]
        position = start + size + (size & 1)
    raise FetchError("converted WAV has no data chunk")


def _pcm16_from_payload(payload: bytes) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(payload)
    return output.getvalue()


def _relative_to_root(spike_root: Path, path: Path) -> PurePosixPath:
    root = spike_root.resolve(strict=True)
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise FetchError(f"output directory escapes the spike root: {path}")
    return PurePosixPath(*resolved.relative_to(root).parts)


def _write_outputs(outputs: dict[Path, bytes], force: bool) -> list[str]:
    actions = []
    # Preflight every path before mutating anything so a refusal cannot leave a
    # half-regenerated fixture set behind.
    if not force:
        for path, data in outputs.items():
            if path.exists() and path.read_bytes() != data:
                raise FetchError(
                    f"refusing to overwrite modified file {path}; use --force or "
                    "--output-dir for an explicit alternate destination"
                )
    for path, data in outputs.items():
        actions.append(f"{write_if_unchanged(path, data, force=force)} {path}")
    return actions


def fetch(
    spike_root: Path,
    *,
    output_dir: Path | None = None,
    cache_dir: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
    prefix_bytes: int = MAX_PREFIX_BYTES,
    verify_only: bool = False,
) -> int:
    root = spike_root.resolve(strict=True)
    output = _ensure_project_local(
        root, output_dir or root / "fixtures", "output directory"
    )
    cache = _ensure_project_local(root, cache_dir or root / ".cache" / "fixtures",
                                  "cache directory")
    if not (MIN_PREFIX_BYTES <= prefix_bytes <= MAX_PREFIX_BYTES):
        raise FetchError(
            f"prefix_bytes must be between {MIN_PREFIX_BYTES} and {MAX_PREFIX_BYTES}"
        )
    manifest_path = output / "manifest.json"
    if verify_only:
        manifest = manifest_tools.load_manifest(manifest_path, root)
        total_bytes = 0
        total_duration = 0.0
        for fixture in manifest["fixtures"]:
            wav = manifest_tools.resolve_manifest_path(
                root, fixture["wav"], fixture["id"]
            )
            ref = manifest_tools.resolve_manifest_path(
                root, fixture["reference"], fixture["id"]
            )
            total_bytes += wav.stat().st_size + ref.stat().st_size
            total_duration += fixture["duration_s"]
        print(
            f"verified {len(manifest['fixtures'])} fixtures, "
            f"{total_bytes} bytes, {total_duration:.3f} s"
        )
        return 0

    relative_dir = _relative_to_root(root, output)
    outputs = build_fixtures(root, cache, prefix_bytes, relative_dir)
    manifest = json.loads(outputs[Path("manifest.json")].decode("utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    final_outputs = {output / path: data for path, data in outputs.items()}
    if dry_run:
        for path, data in sorted(final_outputs.items()):
            print(f"would write {path} ({len(data)} bytes sha256={sha256_bytes(data)})")
        return 0
    actions = _write_outputs(final_outputs, force=force)
    for action in actions:
        print(action)
    manifest_tools.load_manifest(output / "manifest.json", root)
    total_bytes = sum(len(data) for data in final_outputs.values())
    print(
        f"ok: {len(manifest['fixtures'])} fixtures, {total_bytes} output bytes, "
        f"{sum(f['duration_s'] for f in manifest['fixtures']):.3f} s"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch/verify the pinned CC-BY-4.0 FLEURS fixture slice using only "
            "bounded HTTP Range reads (no whole-split downloads)."
        )
    )
    parser.add_argument(
        "--spike-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="spike root containing fixtures/ (default: this tool's spike)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="destination inside the spike (default: <spike>/fixtures)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="download cache inside the spike (default: <spike>/.cache/fixtures)",
    )
    parser.add_argument(
        "--prefix-bytes",
        type=int,
        default=MAX_PREFIX_BYTES,
        help=f"bounded tar.gz Range prefix, {MIN_PREFIX_BYTES}..{MAX_PREFIX_BYTES} "
        f"bytes (default {MAX_PREFIX_BYTES})",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="offline manifest/hash verification; no network access or writes",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="download and convert but print planned outputs instead of writing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="explicitly overwrite differing existing files (off by default)",
    )
    args = parser.parse_args(argv)
    if args.verify_only and args.dry_run:
        parser.error("--verify-only and --dry-run are mutually exclusive")
    try:
        return fetch(
            args.spike_root,
            output_dir=args.output_dir,
            cache_dir=args.cache_dir,
            force=args.force,
            dry_run=args.dry_run,
            prefix_bytes=args.prefix_bytes,
            verify_only=args.verify_only,
        )
    except (FetchError, manifest_tools.FixtureError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
