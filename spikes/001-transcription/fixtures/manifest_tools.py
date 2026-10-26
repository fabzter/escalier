"""Strict, standard-library validation for the spike fixture manifest.

The manifest is deliberately boring and strict: curated fixtures are small,
fully hashed, and their path/audio/reference invariants are checked offline.
Paths in the manifest are POSIX paths relative to the spike root (the directory
containing ``fixtures/``), never relative to the manifest file or the CWD.

One documented value extension is allowed for synthetic multi-language
assemblies: ``language="mixed"`` with ``asr_language="auto"``.  The runner passes
that hint through to the engine, which maps it to its native auto/NULL path.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import wave
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

SCHEMA_VERSION = 1
SAMPLE_RATE = 16000
MAX_DEFAULT_DURATION_S = 20.0
SEGMENT_KINDS = frozenset({"oracle_file_boundary", "derived_assembly"})

_TOP_KEYS = frozenset({"schema_version", "sample_rate", "fixtures"})
_FIXTURE_KEYS = frozenset(
    {
        "id",
        "language",
        "asr_language",
        "wav",
        "reference",
        "wav_sha256",
        "reference_sha256",
        "duration_s",
        "source",
        "conversion",
        "segments",
    }
)
_SOURCE_KEYS = frozenset(
    {
        "url",
        "revision",
        "license",
        "config",
        "locale",
        "split",
        "row",
        "item_id",
        "audio_sha256",
        "reference_column",
    }
)
_CONVERSION_KEYS = frozenset({"tool"})
_SEGMENT_KEYS = frozenset({"start_s", "end_s", "kind"})

_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9A-Fa-f]{7,64}\Z")
# Documented extension for explicitly assembled multi-language fixtures:
# language="mixed" and asr_language="auto" (the engine maps auto to its native
# NULL/empty language hint).  All single-language fixtures keep BCP-47-like tags.
_LANGUAGE = re.compile(r"(?:[a-z]{2,3}|mixed)\Z")
_ASR_LANGUAGE = re.compile(r"(?:auto|[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})?)\Z")
_DRIVE_PREFIX = re.compile(r"[A-Za-z]:")
_COVERAGE_TOL = 1e-6
_DURATION_TOL = 1e-3


class FixtureError(ValueError):
    """A curated fixture or manifest invariant failed."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wav_info(path: Path) -> dict:
    """Return the checked PCM layout of a WAV file."""
    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frames = handle.getnframes()
            compression = handle.getcomptype()
    except (wave.Error, EOFError, OSError) as exc:
        raise FixtureError(f"unreadable WAV {path}: {exc}") from exc
    if compression != "NONE":
        raise FixtureError(f"WAV {path} is compressed ({compression})")
    if channels != 1:
        raise FixtureError(f"WAV {path} must be mono, found {channels} channels")
    if sample_width != 2:
        raise FixtureError(
            f"WAV {path} must be PCM16 (2-byte samples), found {sample_width}"
        )
    if sample_rate != SAMPLE_RATE:
        raise FixtureError(
            f"WAV {path} must be {SAMPLE_RATE} Hz, found {sample_rate} Hz"
        )
    if frames <= 0:
        raise FixtureError(f"WAV {path} has no audio frames")
    return {
        "channels": channels,
        "sample_width": sample_width,
        "sample_rate": sample_rate,
        "frames": frames,
        "duration_s": frames / sample_rate,
    }


def _fail(context: str, message: str) -> None:
    raise FixtureError(f"{context}: {message}")


def _require_mapping(value, context: str, keys: frozenset[str]) -> dict:
    if not isinstance(value, dict):
        _fail(context, f"must be an object, found {type(value).__name__}")
    actual = set(value)
    missing = keys - actual
    extra = actual - keys
    if missing:
        _fail(context, f"missing fields {sorted(missing)}")
    if extra:
        _fail(context, f"unknown fields {sorted(extra)}")
    return value


def _require_str(value, context: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(context, "must be a nonempty string")
    if "\x00" in value:
        _fail(context, "must not contain NUL")
    return value


def _require_int(value, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(context, "must be an integer")
    return value


def _require_number(value, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(context, "must be a number")
    number = float(value)
    if not math.isfinite(number):
        _fail(context, "must be finite")
    return number


def _require_sha256(value, context: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        _fail(context, "must be a lowercase 64-character SHA-256 hex digest")
    return value


def _validate_manifest_path(relative, context: str) -> PurePosixPath:
    if not isinstance(relative, str) or not relative:
        _fail(context, "must be a nonempty relative path")
    if "\x00" in relative or "\\" in relative:
        _fail(context, "must use POSIX separators and contain no NUL")
    if relative.startswith("/") or relative.startswith("./") or relative.endswith("/"):
        _fail(context, "must be a plain relative file path")
    if "//" in relative:
        _fail(context, "must not contain repeated separators")
    if _DRIVE_PREFIX.match(relative):
        _fail(context, "must not be a Windows drive path")
    if any(part in ("", ".", "..") for part in relative.split("/")):
        _fail(context, "must not contain traversal segments or dot components")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        _fail(context, "must not contain traversal segments")
    return pure


def resolve_manifest_path(spike_root: Path, relative, context: str = "path") -> Path:
    """Resolve a manifest path from the spike root and refuse escapes."""
    pure = _validate_manifest_path(relative, context)
    try:
        root = Path(spike_root).resolve(strict=True)
    except OSError as exc:
        raise FixtureError(f"{context}: spike root unavailable: {exc}") from exc
    candidate = root.joinpath(*pure.parts)
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise FixtureError(f"{context}: missing fixture file {candidate}: {exc}") from exc
    if not resolved.is_relative_to(root):
        _fail(context, f"escapes spike root: {candidate}")
    if not resolved.is_file():
        _fail(context, f"is not a regular file: {candidate}")
    return resolved


def _validate_source(source, context: str) -> None:
    _require_mapping(source, context, _SOURCE_KEYS)
    url = _require_str(source["url"], f"{context}.url")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        _fail(f"{context}.url", "must be an absolute https URL")
    if parsed.query or parsed.fragment:
        _fail(f"{context}.url", "must be canonical (no query or fragment)")
    lowered = url.lower()
    for marker in ("x-amz-", "signature=", "token=", "expires="):
        if marker in lowered:
            _fail(f"{context}.url", "must not be a transient signed URL")
    revision = _require_str(source["revision"], f"{context}.revision")
    if not _COMMIT.fullmatch(revision):
        _fail(f"{context}.revision", "must be a pinned hexadecimal revision")
    _require_str(source["license"], f"{context}.license")
    _require_str(source["config"], f"{context}.config")
    _require_str(source["locale"], f"{context}.locale")
    _require_str(source["split"], f"{context}.split")
    row = _require_int(source["row"], f"{context}.row")
    if row < 0:
        _fail(f"{context}.row", "must be nonnegative")
    item_id = _require_str(source["item_id"], f"{context}.item_id")
    if PurePosixPath(item_id).name != item_id or item_id in (".", ".."):
        _fail(f"{context}.item_id", "must be a source filename, not a path")
    _require_sha256(source["audio_sha256"], f"{context}.audio_sha256")
    _require_str(source["reference_column"], f"{context}.reference_column")


def _validate_conversion(conversion, context: str) -> None:
    _require_mapping(conversion, context, _CONVERSION_KEYS)
    _require_str(conversion["tool"], f"{context}.tool")


def _validate_segments(segments, duration_s: float, context: str) -> None:
    if not isinstance(segments, list) or not segments:
        _fail(context, "must be a nonempty list")
    previous_end = None
    for index, raw in enumerate(segments):
        seg_context = f"{context}[{index}]"
        segment = _require_mapping(raw, seg_context, _SEGMENT_KEYS)
        start = _require_number(segment["start_s"], f"{seg_context}.start_s")
        end = _require_number(segment["end_s"], f"{seg_context}.end_s")
        kind = segment["kind"]
        if not isinstance(kind, str) or kind not in SEGMENT_KINDS:
            _fail(f"{seg_context}.kind", f"unsupported segment kind {kind!r}")
        if start < 0:
            _fail(f"{seg_context}.start_s", "must be nonnegative")
        if end <= start:
            _fail(f"{seg_context}.end_s", "must be greater than start_s")
        if previous_end is None:
            if abs(start) > _COVERAGE_TOL:
                _fail(context, "segments must cover the clip from 0.0 s")
        else:
            if start < previous_end - _COVERAGE_TOL:
                _fail(context, "segments must be ordered and nonoverlapping")
            if abs(start - previous_end) > _COVERAGE_TOL:
                _fail(context, "segments must not leave gaps")
        previous_end = end
    assert previous_end is not None
    if abs(previous_end - duration_s) > _DURATION_TOL:
        _fail(
            context,
            f"segments end at {previous_end}s but duration_s is {duration_s}s",
        )
    kinds = {segment["kind"] for segment in segments}
    if len(segments) > 1 and kinds != {"derived_assembly"}:
        _fail(
            context,
            "multi-segment fixtures require explicit derived_assembly segments",
        )
    # A one-piece fixture may be either an original file boundary or an
    # explicitly labelled derived segment.  Multi-piece fixtures are always
    # assemblies and must say so.


def _validate_reference(path: Path, expected_sha256: str, context: str) -> None:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise FixtureError(f"{context}: unreadable reference: {exc}") from exc
    actual = sha256_bytes(data)
    if actual != expected_sha256:
        raise FixtureError(
            f"{context}: reference sha256 mismatch (manifest {expected_sha256}, "
            f"actual {actual})"
        )
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FixtureError(f"{context}: reference is not valid UTF-8: {exc}") from exc
    if "\x00" in text:
        raise FixtureError(f"{context}: reference contains NUL")
    if not text.strip():
        raise FixtureError(f"{context}: reference is empty")


def _validate_wav(
    path: Path, expected_sha256: str, duration_s: float, context: str
) -> None:
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise FixtureError(
            f"{context}: WAV sha256 mismatch (manifest {expected_sha256}, "
            f"actual {actual})"
        )
    info = wav_info(path)
    if abs(info["duration_s"] - duration_s) > _DURATION_TOL:
        raise FixtureError(
            f"{context}: duration_s {duration_s} does not match WAV duration "
            f"{info['duration_s']} ({info['frames']} frames)"
        )


def _validate_fixture(fixture, spike_root: Path, index: int) -> None:
    context = f"fixtures[{index}]"
    _require_mapping(fixture, context, _FIXTURE_KEYS)
    fixture_id = _require_str(fixture["id"], f"{context}.id")
    if not _SAFE_ID.fullmatch(fixture_id) or ".." in fixture_id:
        _fail(f"{context}.id", "must be a safe ID (letters, digits, . _ -)")
    language = _require_str(fixture["language"], f"{context}.language")
    if not _LANGUAGE.fullmatch(language):
        _fail(f"{context}.language", "must be a short lowercase language tag")
    asr_language = _require_str(fixture["asr_language"], f"{context}.asr_language")
    if not _ASR_LANGUAGE.fullmatch(asr_language):
        _fail(f"{context}.asr_language", "must be a BCP-47-like language tag")

    duration = _require_number(fixture["duration_s"], f"{context}.duration_s")
    if duration <= 0:
        _fail(f"{context}.duration_s", "must be positive")
    if duration > MAX_DEFAULT_DURATION_S + _COVERAGE_TOL:
        _fail(
            f"{context}.duration_s",
            f"default fixtures must be <= {MAX_DEFAULT_DURATION_S:g} s",
        )

    wav_sha = _require_sha256(fixture["wav_sha256"], f"{context}.wav_sha256")
    ref_sha = _require_sha256(
        fixture["reference_sha256"], f"{context}.reference_sha256"
    )
    wav_path = resolve_manifest_path(
        spike_root, fixture["wav"], f"{context}.wav"
    )
    ref_path = resolve_manifest_path(
        spike_root, fixture["reference"], f"{context}.reference"
    )
    _validate_source(fixture["source"], f"{context}.source")
    _validate_conversion(fixture["conversion"], f"{context}.conversion")
    _validate_segments(fixture["segments"], duration, f"{context}.segments")
    tool = fixture["conversion"]["tool"].strip().lower()
    if tool == "none" and any(
        segment["kind"] == "derived_assembly"
        for segment in fixture["segments"]
    ):
        _fail(
            f"{context}.conversion.tool",
            "derived_assembly fixtures require an explicit derivation tool",
        )
    _validate_reference(ref_path, ref_sha, f"{context}.reference")
    _validate_wav(wav_path, wav_sha, duration, f"{context}.wav")


def validate_manifest(manifest: dict, spike_root: Path) -> dict:
    """Validate the complete manifest and return it unchanged."""
    _require_mapping(manifest, "manifest", _TOP_KEYS)
    version = _require_int(manifest["schema_version"], "schema_version")
    if version != SCHEMA_VERSION:
        _fail("schema_version", f"expected {SCHEMA_VERSION}, found {version}")
    sample_rate = _require_int(manifest["sample_rate"], "sample_rate")
    if sample_rate != SAMPLE_RATE:
        _fail("sample_rate", f"expected {SAMPLE_RATE}, found {sample_rate}")
    fixtures = manifest["fixtures"]
    if not isinstance(fixtures, list) or not fixtures:
        _fail("fixtures", "must be a nonempty list")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    seen_resolved_paths: set[Path] = set()
    for index, fixture in enumerate(fixtures):
        if not isinstance(fixture, dict):
            _fail(f"fixtures[{index}]", "must be an object")
        fixture_id = fixture.get("id")
        if isinstance(fixture_id, str):
            if fixture_id in seen_ids:
                _fail(f"fixtures[{index}].id", f"duplicate ID {fixture_id!r}")
            seen_ids.add(fixture_id)
        for field in ("wav", "reference"):
            value = fixture.get(field)
            if isinstance(value, str):
                if value in seen_paths:
                    _fail(f"fixtures[{index}].{field}", f"duplicate path {value!r}")
                seen_paths.add(value)

        _validate_fixture(fixture, spike_root, index)
        for field in ("wav", "reference"):
            resolved = resolve_manifest_path(
                spike_root,
                fixture[field],
                f"fixtures[{index}].{field}",
            )
            if resolved in seen_resolved_paths:
                _fail(
                    f"fixtures[{index}].{field}",
                    f"duplicate resolved path {resolved}",
                )
            seen_resolved_paths.add(resolved)

    return manifest


def _reject_constant(value: str):
    raise FixtureError(f"nonfinite JSON constant {value!r}")


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise FixtureError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_manifest(manifest_path: Path, spike_root: Path) -> dict:
    """Load strict JSON and validate the manifest against ``spike_root``."""
    try:
        raw = Path(manifest_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise FixtureError(f"cannot read manifest {manifest_path}: {exc}") from exc
    try:
        manifest = json.loads(
            raw,
            parse_constant=_reject_constant,
            object_pairs_hook=_reject_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise FixtureError(f"invalid manifest JSON: {exc}") from exc
    return validate_manifest(manifest, spike_root)
