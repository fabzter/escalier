#!/usr/bin/env python3
"""Paced replay runner for the transcription feasibility spike.

Arms
----
``endpoint``
    Batch-decode each oracle fixture segment when its end arrives.  This is the
    endpoint-only baseline; boundaries come from fixture metadata, never a
    tested VAD.
``hybrid``
    Fixed-start growing-prefix batch decoding with runner word-level
    LocalAgreement-2.  Before every call the prefix is frozen at
    ``min(selected_tick, arrived_samples)``; slow calls coalesce missed ticks
    instead of replaying every stale prefix.
``native-stream``
    Genuine ``Engine.start_stream`` / ``Engine.feed`` streaming.  Every arrived
    sample is fed exactly once and in order; a slow feed may coalesce caller
    cadence ticks for display bookkeeping but never drops audio.

Only arrived fixture audio is ever decoded.  Real time comes from
``time.monotonic``; deterministic tests inject :class:`FakeClock` and fake
engines.  Fake-clock timings populate only ``simulated`` fields.

The manifest validator is the fixture slice's strict, stdlib-only
``fixtures/manifest_tools.py``; this runner adds selection and the configured
max-window policy.  The heavy native backend is imported lazily so pure tests
run without a built helper.
"""

from __future__ import annotations

import argparse
import array
import copy
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import metrics
import policy

SPIKE_ROOT = Path(__file__).resolve().parent
ARMS = ("endpoint", "hybrid", "native-stream")
CLOCK_MODES = ("real", "fake")

# Binding experiment design: the native-stream comparison is nominal R=3;
# the documented offline batch setting is R=13.  An R=13 native run is an
# explicit control, never the default.  These are documented/documented-API
# values, not evidence of the context actually applied by a native call.
NATIVE_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES = 3
OFFLINE_BATCH_ATT_CONTEXT_RIGHT_FRAMES = 13
DOCUMENTED_MODEL_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES = 13


def context_metadata(arm: str, right_context_frames: int) -> dict:
    """Describe the per-arm context/lookahead setting and its confound."""
    if arm not in ARMS:
        raise ValueError(f"unsupported arm {arm!r}")
    if arm == "native-stream":
        requested = int(right_context_frames)
        if requested == NATIVE_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES:
            label = "native_R=3"
            confound = (
                "Nominal native streaming R=3 versus documented offline batch "
                "R=13 differs in both lookahead and architecture; it is not an "
                "isolated accuracy comparison."
            )
            limitation = (
                "Native streaming uses the binding native R=3 setting; the "
                "documented offline batch setting is R=13, so the comparison "
                "confounds lookahead with architecture. Requested R=3 is not "
                "proof of applied native context unless engine.info reports it."
            )
        else:
            label = f"native_R={requested}_explicit_control"
            confound = (
                f"Explicit native R={requested} control run, not the specified "
                "native R=3 condition. Do not present it as the R=3-vs-R=13 "
                "lookahead comparison; architecture still differs from offline "
                "batch decoding."
            )
            limitation = (
                f"Native streaming ran with explicit control R={requested}, not "
                "the specified native R=3 condition; this is a labelled control "
                "run, not the binding R=3-vs-offline-R=13 comparison. Applied "
                "context is only what engine.info reports."
            )
        return {
            "context_label": label,
            "arm": arm,
            "native_stream": True,
            "requested_att_context_right_frames": requested,
            "native_default_att_context_right_frames": NATIVE_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES,
            "documented_model_default_att_context_right_frames": DOCUMENTED_MODEL_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES,
            "documented_offline_batch_right_context_frames": OFFLINE_BATCH_ATT_CONTEXT_RIGHT_FRAMES,
            "stream_latency_setting": (
                f"native_stream.att_context_right_frames requested={requested}; "
                "applied context is engine-reported only, never inferred from "
                "the request"
            ),
            "context_confound": confound,
            "limitation": limitation,
        }
    return {
        "context_label": "offline_batch_R=13",
        "arm": arm,
        "native_stream": False,
        "requested_att_context_right_frames": None,
        "native_default_att_context_right_frames": NATIVE_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES,
        "documented_model_default_att_context_right_frames": DOCUMENTED_MODEL_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES,
        "documented_offline_batch_right_context_frames": OFFLINE_BATCH_ATT_CONTEXT_RIGHT_FRAMES,
        "stream_latency_setting": (
            "offline_batch_documented_R=13; not native streaming; native "
            "streaming lookahead is not applicable"
        ),
        "context_confound": (
            "Endpoint/hybrid batch decoding uses the documented offline R=13 "
            "context; results are not native-streaming latency evidence."
        ),
        "limitation": (
            "Endpoint/hybrid batch decoding is labelled as documented offline "
            "R=13 context; native streaming R=3 lookahead is not measured by "
            "this arm."
        ),
    }

_SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
_TRIAL_TOKEN = re.compile(r"[^A-Za-z0-9._-]+")


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SpikeError(Exception):
    """Base class for runner/CLI failures."""


class ManifestError(SpikeError):
    """The manifest or one selected fixture failed validation."""


class FixtureError(ManifestError):
    """A selected fixture's bytes/layout do not satisfy the manifest."""


class UnsupportedWindowError(SpikeError):
    """A fixture or prefix exceeds the configured fixed-start window limit."""


class OutputCollisionError(SpikeError):
    """The requested output exists and overwrite was not requested."""


class CapabilityError(SpikeError):
    """The engine explicitly reports a capability the arm requires as absent."""


class EngineCallError(SpikeError):
    """One engine call failed; recorded as a trial error, never as fake success."""


# ---------------------------------------------------------------------------
# Manifest consumption
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Segment:
    start_s: float
    end_s: float
    kind: str

    def as_dict(self) -> dict:
        return {"start_s": self.start_s, "end_s": self.end_s, "kind": self.kind}


@dataclass
class Fixture:
    id: str
    language: str
    asr_language: str | None
    wav_relative: str
    reference_relative: str
    wav_path: Path
    reference_path: Path
    wav_sha256: str
    reference_sha256: str
    duration_s: float
    samples: array.array
    sample_rate: int
    reference_text: str
    source: dict
    conversion: dict
    segments: list[Segment]

    def identity(self) -> dict:
        return {
            "id": self.id,
            "language": self.language,
            "asr_language": self.asr_language,
            "wav": {"relative": self.wav_relative, "sha256": self.wav_sha256},
            "reference": {
                "relative": self.reference_relative,
                "sha256": self.reference_sha256,
            },
            "duration_s": self.duration_s,
            "sample_rate": self.sample_rate,
            "source": sanitize_metadata(self.source),
            "conversion": sanitize_metadata(self.conversion),
            "segments": [segment.as_dict() for segment in self.segments],
        }


@dataclass
class Manifest:
    schema_version: int
    sample_rate: int
    path: Path
    spike_root: Path
    fixtures: list[Fixture]
    sha256: str


_MANIFEST_TOOLS: Any = None


def _manifest_tools() -> Any:
    global _MANIFEST_TOOLS
    if _MANIFEST_TOOLS is None:
        path = SPIKE_ROOT / "fixtures" / "manifest_tools.py"
        if not path.is_file():
            raise ManifestError(
                "fixtures/manifest_tools.py is missing; the fixture manifest "
                "validator is required to consume curated fixtures"
            )
        spec = importlib.util.spec_from_file_location(
            "_escalier_spike_manifest_tools", path
        )
        if spec is None or spec.loader is None:
            raise ManifestError(f"cannot load manifest validator from {path.name}")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # pragma: no cover - broken sibling install
            raise ManifestError(
                f"cannot import fixtures/manifest_tools.py: {type(exc).__name__}: {exc}"
            ) from exc
        _MANIFEST_TOOLS = module
    return _MANIFEST_TOOLS


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_pcm16_samples(path: Path, expected_frames: int) -> array.array:
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            raw = handle.readframes(frames)
    except (wave.Error, EOFError, OSError) as exc:
        raise FixtureError(f"unreadable WAV {Path(path).name}: {exc}") from exc
    if frames != expected_frames or len(raw) != frames * 2:
        raise FixtureError(
            f"WAV {Path(path).name}: frame/byte count changed during validation"
        )
    pcm = array.array("h")
    pcm.frombytes(raw)
    if sys.byteorder == "big":
        pcm.byteswap()
    return array.array("d", (value / 32768.0 for value in pcm))


def load_manifest(
    manifest_path: Path,
    *,
    spike_root: Path | None = None,
    max_window_ms: int = 20000,
    only_ids: Sequence[str] | None = None,
) -> Manifest:
    """Validate the manifest, select fixtures and enforce the window policy.

    Every entry is fully validated by ``fixtures/manifest_tools.py`` before
    selection, including its hashes, WAV layout and its own default ≤20 s cap.
    Selection filtering happens after that validation, so the shared validator
    can reject a manifest containing a longer clip regardless of ``only_ids``.
    After selection, selected clips above ``max_window_ms`` are rejected
    explicitly rather than truncated. ``max_window_ms`` can be stricter than
    the shared validator's cap, but it cannot relax that cap.
    """
    if isinstance(max_window_ms, bool) or not isinstance(max_window_ms, int):
        raise ValueError("max_window_ms must be an integer")
    if max_window_ms <= 0:
        raise ValueError("max_window_ms must be positive")
    root = Path(spike_root if spike_root is not None else SPIKE_ROOT).resolve()
    manifest_path = Path(manifest_path)
    tools = _manifest_tools()
    try:
        raw = tools.load_manifest(manifest_path, root)
    except tools.FixtureError as exc:
        raise ManifestError(str(exc)) from exc

    entries = raw["fixtures"]
    all_ids = [entry["id"] for entry in entries]
    if only_ids is not None:
        requested = list(dict.fromkeys(only_ids))
        unknown = [value for value in requested if value not in set(all_ids)]
        if unknown:
            raise ManifestError(f"unknown fixture id(s): {', '.join(unknown)}")
        selected_ids = set(requested)
        selected = [entry for entry in entries if entry["id"] in selected_ids]
        if not selected:
            raise ManifestError("no fixtures selected by --fixture")
    else:
        selected = list(entries)

    fixtures: list[Fixture] = []
    for entry in selected:
        context = f"fixtures[{entry['id']}]"
        try:
            wav_path = tools.resolve_manifest_path(root, entry["wav"], f"{context}.wav")
            reference_path = tools.resolve_manifest_path(
                root, entry["reference"], f"{context}.reference"
            )
            info = tools.wav_info(wav_path)
        except tools.FixtureError as exc:
            raise FixtureError(str(exc)) from exc

        duration_ms = info["duration_s"] * 1000.0
        if duration_ms > max_window_ms + 1e-6:
            raise UnsupportedWindowError(
                f"fixture {entry['id']!r} duration {info['duration_s']:.3f}s "
                f"exceeds max window {max_window_ms / 1000.0:.3f}s; long-call "
                "rollover/rolling windows are unsupported and evidence is not "
                "silently truncated"
            )

        try:
            samples = _read_pcm16_samples(wav_path, info["frames"])
            reference_text = reference_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise FixtureError(f"{context}: cannot read fixture bytes: {exc}") from exc

        fixtures.append(
            Fixture(
                id=entry["id"],
                language=entry["language"],
                asr_language=entry.get("asr_language"),
                wav_relative=entry["wav"],
                reference_relative=entry["reference"],
                wav_path=wav_path,
                reference_path=reference_path,
                wav_sha256=entry["wav_sha256"],
                reference_sha256=entry["reference_sha256"],
                duration_s=info["duration_s"],
                samples=samples,
                sample_rate=info["sample_rate"],
                reference_text=reference_text,
                source=copy.deepcopy(entry["source"]),
                conversion=copy.deepcopy(entry["conversion"]),
                segments=[
                    Segment(
                        start_s=float(segment["start_s"]),
                        end_s=float(segment["end_s"]),
                        kind=segment["kind"],
                    )
                    for segment in entry["segments"]
                ],
            )
        )

    return Manifest(
        schema_version=raw["schema_version"],
        sample_rate=raw["sample_rate"],
        path=manifest_path,
        spike_root=root,
        fixtures=fixtures,
        sha256=file_sha256(manifest_path),
    )


# ---------------------------------------------------------------------------
# Privacy-safe metadata helpers
# ---------------------------------------------------------------------------

_HOME = str(Path.home())
_PATH_KEYS = {
    "path",
    "paths",
    "dir",
    "directory",
    "file",
    "cache",
    "root",
    "model",
    "library",
    "manifest",
    "output",
    "executable",
    "workdir",
}


def _pathish_key(key: str | None) -> bool:
    if not key:
        return False
    lowered = key.lower()
    return (
        lowered in _PATH_KEYS
        or lowered.endswith("_path")
        or lowered.endswith("_dir")
        or lowered.endswith("_directory")
        or lowered.endswith("_file")
        or lowered.endswith("_root")
    )


def sanitize_metadata(value: Any, *, _key: str | None = None) -> Any:
    """Make metadata JSON-safe and avoid publishing private home paths.

    Nonfinite floats become ``None`` (unknown) rather than JSON extensions.
    Path-like fields under the current home directory are reduced to a basename;
    other strings are redacted to ``<home>``.  Transcript/event text is not sent
    through this helper, so raw model output is preserved.
    """
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        if _HOME and _HOME in value:
            if _pathish_key(_key) and not any(char.isspace() for char in value):
                return Path(value).name
            return value.replace(_HOME, "<home>")
        return value
    if isinstance(value, dict):
        return {
            str(key): sanitize_metadata(item, _key=str(key))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_metadata(item, _key=_key) for item in value]
    if isinstance(value, Path):
        return sanitize_metadata(str(value), _key=_key)
    if isinstance(value, bytes):
        return {
            "type": "bytes",
            "length": len(value),
            "sha256": hashlib.sha256(value).hexdigest(),
        }
    return sanitize_metadata(str(value), _key=_key)


def _redact(text: Any) -> str:
    value = sanitize_metadata(str(text))
    return value if isinstance(value, str) else str(value)


def _public_path(path: Path | str) -> str:
    candidate = Path(path).expanduser()
    try:
        resolved = candidate.resolve()
    except OSError:
        return candidate.name
    try:
        return resolved.relative_to(SPIKE_ROOT).as_posix()
    except ValueError:
        return resolved.name


def _finite_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _positive_ms_or_none(value: Any) -> float | None:
    """Native timing convention: zero or negative means unknown, never known-zero."""
    number = _finite_or_none(value)
    if number is None or number <= 0:
        return None
    return number


# ---------------------------------------------------------------------------
# Replay configuration, clocks and scheduler
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReplayConfig:
    arm: str
    clock_mode: str = "real"
    partial_interval_ms: int = 500
    feed_chunk_ms: int = 1120
    max_window_ms: int = 20000
    right_context_frames: int = NATIVE_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES
    commit_policy: str = "stable-prefix"
    agreement_n: int = 2
    engine_language: str = "auto"
    asr_language_override: str | None = None
    window_mode: str = "fixed-start"

    def __post_init__(self) -> None:
        if self.arm not in ARMS:
            raise ValueError(f"unsupported arm {self.arm!r}; choose from {ARMS}")
        if self.clock_mode not in CLOCK_MODES:
            raise ValueError(f"unsupported clock mode {self.clock_mode!r}")
        for field_name in (
            "partial_interval_ms",
            "feed_chunk_ms",
            "max_window_ms",
            "agreement_n",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{field_name} must be a positive integer")
        if (
            isinstance(self.right_context_frames, bool)
            or not isinstance(self.right_context_frames, int)
            or self.right_context_frames < 0
        ):
            raise ValueError("right_context_frames must be a nonnegative integer")
        if not isinstance(self.commit_policy, str) or not self.commit_policy:
            raise ValueError("commit_policy must be a nonempty string")
        if self.window_mode != "fixed-start":
            raise UnsupportedWindowError(
                "only fixed-start growing-prefix windows are supported; rolling/"
                "long-call window behavior is intentionally rejected"
            )
        if self.asr_language_override is not None and not isinstance(
            self.asr_language_override, str
        ):
            raise ValueError("asr_language_override must be a string or None")


class RealClock:
    """Monotonic wall clock with a sleep that tolerates early wake-ups."""

    def now(self) -> float:
        return time.monotonic()

    def sleep_until(self, target: float) -> None:
        while True:
            delay = target - self.now()
            if delay <= 0:
                return
            time.sleep(delay)


class FakeClock:
    """Deterministic fake clock; engine doubles advance it to simulate decode work."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = float(start)
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self._now

    def sleep_until(self, target: float) -> None:
        if target > self._now:
            self._now = float(target)
        self.sleeps.append(float(target))

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("cannot move the fake clock backwards")
        self._now += float(seconds)


def _round_ms_from_seconds(value: float) -> float:
    return round(value * 1000.0, 3)


def _round3(value: float) -> float:
    return round(float(value), 3)


class ReplayRunner:
    """Run one arm over one fixture using an injected engine and clock."""

    def __init__(self, engine: Any, clock: Any, config: ReplayConfig) -> None:
        self.engine = engine
        self.clock = clock
        self.config = config

    # -- public ---------------------------------------------------------

    def run(
        self,
        fixture: Fixture,
        *,
        phase: str = "measured",
        trial_index: int = 0,
        repeat_index: int = 0,
    ) -> dict:
        trial_id = self._trial_id(fixture, phase, repeat_index)
        sample_rate = fixture.sample_rate
        sample_count = len(fixture.samples)
        duration_ms = sample_count / sample_rate * 1000.0
        if duration_ms > self.config.max_window_ms + 1e-6:
            raise UnsupportedWindowError(
                f"fixture {fixture.id!r} duration {duration_ms / 1000.0:.3f}s "
                f"exceeds max window {self.config.max_window_ms / 1000.0:.3f}s; "
                "rolling windows are unsupported and evidence is not truncated"
            )

        setup: dict = {}
        try:
            if self.config.arm == "native-stream":
                setup["native_start"] = self._start_native_stream(fixture)
            t0 = self.clock.now()
            if self.config.arm == "endpoint":
                bundle = self._run_endpoint(fixture, t0)
            elif self.config.arm == "hybrid":
                bundle = self._run_hybrid(fixture, t0)
            else:
                bundle = self._run_native(fixture, t0)
            return self._build_ok_trial(
                fixture,
                phase=phase,
                trial_index=trial_index,
                repeat_index=repeat_index,
                trial_id=trial_id,
                t0=t0,
                bundle=bundle,
                setup=setup,
            )
        except EngineCallError as exc:
            return self._non_ok_trial(
                fixture,
                phase=phase,
                trial_index=trial_index,
                repeat_index=repeat_index,
                trial_id=trial_id,
                status="error",
                error_type=type(exc).__name__,
                message=_redact(str(exc)),
                fatal_stream_state=self.config.arm == "native-stream",
            )

    def non_ok_trial(
        self,
        fixture: Fixture,
        *,
        phase: str,
        trial_index: int,
        repeat_index: int,
        status: str,
        reason: str,
    ) -> dict:
        return self._non_ok_trial(
            fixture,
            phase=phase,
            trial_index=trial_index,
            repeat_index=repeat_index,
            trial_id=self._trial_id(fixture, phase, repeat_index),
            status=status,
            error_type="Skipped" if status == "skipped" else "Error",
            message=reason,
            fatal_stream_state=False,
        )

    # -- setup helpers --------------------------------------------------

    def _trial_id(self, fixture: Fixture, phase: str, repeat_index: int) -> str:
        raw = f"{phase}-{fixture.id}-{self.config.arm}-r{repeat_index}"
        return _TRIAL_TOKEN.sub("-", raw)

    def _language_for(self, fixture: Fixture) -> tuple[str | None, str]:
        if self.config.asr_language_override:
            return self.config.asr_language_override, "cli_override"
        if fixture.asr_language:
            return fixture.asr_language, "fixture.asr_language"
        return None, "engine_default"

    def _invoke(self, label: str, function: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except Exception as exc:
            raise EngineCallError(
                f"{label}: {type(exc).__name__}: {exc}"
            ) from exc

    def _start_native_stream(self, fixture: Fixture) -> dict:
        language, _source = self._language_for(fixture)
        requested = {
            "feed_chunk_ms": self.config.feed_chunk_ms,
            "att_context_right_frames": self.config.right_context_frames,
            "language": language,
            "commit_policy": self.config.commit_policy,
            "agreement_n": self.config.agreement_n,
        }
        call_start = self.clock.now()
        returned = self._invoke(
            "start_stream", self.engine.start_stream, **requested
        )
        call_end = self.clock.now()
        return {
            "requested": requested,
            "call_wall_ms": _round_ms_from_seconds(call_end - call_start),
            "returned": sanitize_metadata(returned)
            if isinstance(returned, dict)
            else None,
        }

    @staticmethod
    def _arrived(now: float, t0: float, fixture: Fixture) -> int:
        elapsed = max(0.0, now - t0)
        count = int(math.floor(elapsed * fixture.sample_rate + 1e-6))
        return max(0, min(len(fixture.samples), count))

    @staticmethod
    def _tick_time(t0: float, index: int, interval_ms: int) -> float:
        return t0 + index * interval_ms / 1000.0

    @staticmethod
    def _tick_sample(index: int, interval_ms: int, fixture: Fixture) -> int:
        value = int(round(index * interval_ms * fixture.sample_rate / 1000.0))
        return max(0, min(len(fixture.samples), value))

    def _last_partial_tick(self, fixture: Fixture, interval_ms: int) -> int:
        duration_ms = len(fixture.samples) / fixture.sample_rate * 1000.0
        return max(0, int(math.ceil(duration_ms / interval_ms - 1e-9)) - 1)

    def _latest_eligible_tick(
        self,
        now: float,
        t0: float,
        last_tick: int,
        fixture: Fixture,
        interval_ms: int,
    ) -> int:
        elapsed_ms = max(0.0, now - t0) * 1000.0
        candidate = min(last_tick, int(math.floor(elapsed_ms / interval_ms + 1e-9)))
        arrived = self._arrived(now, t0, fixture)
        while candidate >= 1 and self._tick_sample(candidate, interval_ms, fixture) > arrived:
            candidate -= 1
        return max(0, candidate)

    def _check_window(self, samples: int, fixture: Fixture) -> None:
        limit = self.config.max_window_ms * fixture.sample_rate / 1000.0
        if samples > limit + 1e-6:
            raise UnsupportedWindowError(
                f"fixture {fixture.id!r}: frozen prefix {samples} samples "
                f"({samples / fixture.sample_rate * 1000.0:.1f} ms) exceeds "
                f"max window {self.config.max_window_ms} ms; rolling windows are "
                "unsupported and evidence is not truncated"
            )

    def _timing_block(
        self,
        *,
        t0: float,
        scheduled_t: float,
        call_start: float,
        call_end: float,
        prefix_samples: int,
        arrived_before: int,
        arrived_after: int,
        fixture: Fixture,
    ) -> dict:
        sample_rate = fixture.sample_rate
        return {
            "clock": "fake_clock_simulated"
            if self.config.clock_mode == "fake"
            else "real_monotonic_measured",
            "scheduled_ms": _round_ms_from_seconds(scheduled_t - t0),
            "call_start_ms": _round_ms_from_seconds(call_start - t0),
            "call_end_ms": _round_ms_from_seconds(call_end - t0),
            "call_wall_ms": _round_ms_from_seconds(call_end - call_start),
            "queue_lag_ms": _round_ms_from_seconds(call_start - scheduled_t),
            "frozen_prefix_samples": int(prefix_samples),
            "frozen_horizon_ms": _round3(prefix_samples / sample_rate * 1000.0),
            "arrived_samples": int(arrived_before),
            "arrived_horizon_ms": _round3(arrived_before / sample_rate * 1000.0),
            "backlog_samples": max(0, int(arrived_before) - int(prefix_samples)),
            "arrived_samples_after": int(arrived_after),
            "backlog_samples_after": max(
                0, int(arrived_after) - int(prefix_samples)
            ),
        }

    def _normalize_result(self, result: Any) -> dict:
        if not isinstance(result, dict):
            raise EngineCallError(
                f"engine returned {type(result).__name__}, expected a mapping"
            )
        text = result.get("text", "")
        if text is None:
            text = ""
        if not isinstance(text, str):
            raise EngineCallError("engine result.text must be a string or null")
        native: dict = {}
        present: list[str] = []
        for name in (
            "committed_text",
            "tentative_text",
            "display_text",
            "final_text",
        ):
            if name in result:
                present.append(name)
                value = result.get(name)
                native[name] = value if isinstance(value, str) else None
            else:
                native[name] = None
        language_names = (
            "language",
            "requested_language",
            "resolved_language",
            "detected_language",
            "lid_supported",
        )
        language_hints: dict = {}
        for name in language_names:
            if name in result:
                value = result.get(name)
                if value is None or isinstance(value, (str, bool, int)):
                    language_hints[name] = value
                else:
                    language_hints[name] = sanitize_metadata(value)
        core_keys = {
            "text",
            "tokens",
            "decode_ms",
            "final",
            "committed_text",
            "tentative_text",
            "display_text",
            "final_text",
            *language_names,
        }
        native_extra = {
            str(name): sanitize_metadata(value)
            for name, value in result.items()
            if name not in core_keys
        }
        return {
            "text": text,
            "tokens": _sanitize_tokens(result.get("tokens")),
            "decode_ms": _positive_ms_or_none(result.get("decode_ms")),
            "final": bool(result.get("final", False)),
            "native": native,
            "native_fields_present": present,
            "native_extra": native_extra,
            "language_hints": language_hints,
        }

    # -- arm implementations -------------------------------------------

    def _run_hybrid(self, fixture: Fixture, t0: float) -> dict:
        cfg = self.config
        sample_rate = fixture.sample_rate
        audio_end_t = t0 + len(fixture.samples) / sample_rate
        language, _source = self._language_for(fixture)
        stable_policy = policy.StablePrefixPolicy()
        events: list[dict] = []
        last_tick = self._last_partial_tick(fixture, cfg.partial_interval_ms)
        selected = 1
        pending_coalesced: list[int] = []
        display_text: str | None = None
        tentative_text: str | None = None

        while selected <= last_tick:
            scheduled = self._tick_time(t0, selected, cfg.partial_interval_ms)
            if self.clock.now() < scheduled:
                self.clock.sleep_until(scheduled)
            now = self.clock.now()
            if now >= audio_end_t - 1e-12:
                pending_coalesced = list(range(selected, last_tick + 1))
                break
            arrived = self._arrived(now, t0, fixture)
            prefix = min(
                self._tick_sample(selected, cfg.partial_interval_ms, fixture),
                arrived,
            )
            self._check_window(prefix, fixture)
            call_start = now
            result = self._invoke(
                "transcribe",
                self.engine.transcribe,
                fixture.samples[:prefix],
                sample_rate=sample_rate,
                language=language,
            )
            call_end = self.clock.now()
            normalized = self._normalize_result(result)
            update = stable_policy.update(
                normalized["text"], event_index=len(events)
            )
            display_text = update.display_text
            tentative_text = update.tentative_text
            arrived_after = self._arrived(call_end, t0, fixture)
            events.append(
                {
                    "event_index": len(events),
                    "kind": "partial",
                    "selected_tick": selected,
                    "completed_tick": selected,
                    "coalesced_ticks": [],
                    "next_selected_tick": None,
                    "text": normalized["text"],
                    "tokens": normalized["tokens"],
                    "decode_ms": normalized["decode_ms"],
                    "final": normalized["final"],
                    "native": normalized["native"],
                    "native_fields_present": normalized["native_fields_present"],
                    "native_extra": normalized["native_extra"],
                    "language_hints": normalized["language_hints"],
                    "policy": update.as_dict(),
                    "native_commit": None,
                    "timing": self._timing_block(
                        t0=t0,
                        scheduled_t=scheduled,
                        call_start=call_start,
                        call_end=call_end,
                        prefix_samples=prefix,
                        arrived_before=arrived,
                        arrived_after=arrived_after,
                        fixture=fixture,
                    ),
                }
            )

            if call_end >= audio_end_t - 1e-12:
                pending_coalesced = list(range(selected + 1, last_tick + 1))
                break
            latest = self._latest_eligible_tick(
                call_end, t0, last_tick, fixture, cfg.partial_interval_ms
            )
            if latest > selected:
                events[-1]["coalesced_ticks"] = list(range(selected + 1, latest))
                events[-1]["next_selected_tick"] = latest
                selected = latest
            else:
                selected += 1

        self.clock.sleep_until(audio_end_t)
        now = self.clock.now()
        arrived = self._arrived(now, t0, fixture)
        self._check_window(arrived, fixture)
        call_start = now
        result = self._invoke(
            "transcribe_final",
            self.engine.transcribe,
            fixture.samples[:arrived],
            sample_rate=sample_rate,
            language=language,
        )
        call_end = self.clock.now()
        normalized = self._normalize_result(result)
        final_event_index = len(events)
        finalization = stable_policy.finalize(
            normalized["text"], event_index=final_event_index
        )
        events.append(
            {
                "event_index": final_event_index,
                "kind": "final",
                "selected_tick": None,
                "completed_tick": None,
                "coalesced_ticks": pending_coalesced,
                "next_selected_tick": None,
                "text": normalized["text"],
                "tokens": normalized["tokens"],
                "decode_ms": normalized["decode_ms"],
                "final": True,
                "native": normalized["native"],
                "native_fields_present": normalized["native_fields_present"],
                "native_extra": normalized["native_extra"],
                "language_hints": normalized["language_hints"],
                "policy": None,
                "native_commit": None,
                "finalization": {
                    "stable_text": finalization["stable_text"],
                    "final_correction": finalization["final_correction"],
                },
                "timing": self._timing_block(
                    t0=t0,
                    scheduled_t=audio_end_t,
                    call_start=call_start,
                    call_end=call_end,
                    prefix_samples=arrived,
                    arrived_before=arrived,
                    arrived_after=arrived,
                    fixture=fixture,
                ),
            }
        )

        return {
            "events": events,
            "final_text": normalized["text"],
            "stable_text": finalization["stable_text"],
            "display_text": display_text,
            "tentative_text": tentative_text,
            "stable_history": stable_policy.history,
            "conflicts": stable_policy.conflicts,
            "final_correction": finalization["final_correction"],
            "arm_settings": {
                "partial_interval_ms": cfg.partial_interval_ms,
                "runner_local_agreement_n": policy.AGREEMENT_N,
                "max_window_ms": cfg.max_window_ms,
                "window_mode": cfg.window_mode,
            },
        }

    def _run_endpoint(self, fixture: Fixture, t0: float) -> dict:
        cfg = self.config
        sample_rate = fixture.sample_rate
        audio_end_t = t0 + len(fixture.samples) / sample_rate
        language, _source = self._language_for(fixture)
        events: list[dict] = []
        text_parts: list[str] = []

        if not fixture.segments:
            raise SpikeError(f"fixture {fixture.id!r} has no oracle segments")
        for segment_index, segment in enumerate(fixture.segments):
            start_sample = max(
                0, min(len(fixture.samples), int(round(segment.start_s * sample_rate)))
            )
            end_sample = max(
                start_sample,
                min(len(fixture.samples), int(round(segment.end_s * sample_rate))),
            )
            if end_sample <= start_sample:
                raise SpikeError(
                    f"fixture {fixture.id!r} segment {segment_index} has no samples"
                )
            self._check_window(end_sample, fixture)
            scheduled = t0 + segment.end_s
            if self.clock.now() < scheduled:
                self.clock.sleep_until(scheduled)
            now = self.clock.now()
            arrived = self._arrived(now, t0, fixture)
            call_start = now
            result = self._invoke(
                "transcribe_segment",
                self.engine.transcribe,
                fixture.samples[start_sample:end_sample],
                sample_rate=sample_rate,
                language=language,
            )
            call_end = self.clock.now()
            normalized = self._normalize_result(result)
            if normalized["text"].strip():
                text_parts.append(normalized["text"].strip())
            events.append(
                {
                    "event_index": len(events),
                    "kind": "endpoint",
                    "selected_tick": None,
                    "completed_tick": None,
                    "coalesced_ticks": [],
                    "next_selected_tick": None,
                    "endpoint": {
                        "segment_index": segment_index,
                        "start_s": segment.start_s,
                        "end_s": segment.end_s,
                        "kind": segment.kind,
                        "segment_samples": end_sample - start_sample,
                    },
                    "text": normalized["text"],
                    "tokens": normalized["tokens"],
                    "decode_ms": normalized["decode_ms"],
                    "final": normalized["final"],
                    "native": normalized["native"],
                    "native_fields_present": normalized["native_fields_present"],
                    "native_extra": normalized["native_extra"],
                    "language_hints": normalized["language_hints"],
                    "policy": None,
                    "native_commit": None,
                    "timing": self._timing_block(
                        t0=t0,
                        scheduled_t=scheduled,
                        call_start=call_start,
                        call_end=call_end,
                        prefix_samples=end_sample,
                        arrived_before=arrived,
                        arrived_after=self._arrived(call_end, t0, fixture),
                        fixture=fixture,
                    ),
                }
            )

        final_text = " ".join(text_parts)
        return {
            "events": events,
            "final_text": final_text,
            "stable_text": None,
            "display_text": None,
            "tentative_text": None,
            "stable_history": [],
            "conflicts": [],
            "final_correction": None,
            "arm_settings": {
                "endpoint_mode": "per_oracle_segment_batch",
                "max_window_ms": cfg.max_window_ms,
                "window_mode": cfg.window_mode,
            },
        }

    def _run_native(self, fixture: Fixture, t0: float) -> dict:
        cfg = self.config
        sample_rate = fixture.sample_rate
        audio_end_t = t0 + len(fixture.samples) / sample_rate
        events: list[dict] = []
        tracker = policy.NativeCommitTracker()
        last_tick = self._last_partial_tick(fixture, cfg.feed_chunk_ms)
        selected = 1
        fed = 0
        pending_coalesced: list[int] = []
        display_text: str | None = None
        tentative_text: str | None = None

        while selected <= last_tick:
            scheduled = self._tick_time(t0, selected, cfg.feed_chunk_ms)
            if self.clock.now() < scheduled:
                self.clock.sleep_until(scheduled)
            now = self.clock.now()
            if now >= audio_end_t - 1e-12:
                pending_coalesced = list(range(selected, last_tick + 1))
                break
            arrived = self._arrived(now, t0, fixture)
            if arrived <= fed:
                selected += 1
                continue
            chunk = fixture.samples[fed:arrived]
            call_start = now
            result = self._invoke("feed", self.engine.feed, chunk, final=False)
            call_end = self.clock.now()
            normalized = self._normalize_result(result)
            fed_before = fed
            fed = arrived
            native_commit = self._track_native_commit(
                tracker, normalized, event_index=len(events)
            )
            if normalized["native"]["display_text"] is not None:
                display_text = normalized["native"]["display_text"]
            elif normalized["native"]["tentative_text"] is not None:
                display_text = normalized["native"]["tentative_text"]
            if normalized["native"]["tentative_text"] is not None:
                tentative_text = normalized["native"]["tentative_text"]
            events.append(
                {
                    "event_index": len(events),
                    "kind": "feed",
                    "selected_tick": selected,
                    "completed_tick": selected,
                    "coalesced_ticks": [],
                    "next_selected_tick": None,
                    "chunk_samples": len(chunk),
                    "fed_before_samples": fed_before,
                    "fed_after_samples": fed,
                    "nominal_chunk_ms": cfg.feed_chunk_ms,
                    "effective_chunk_ms": _round3(
                        len(chunk) / sample_rate * 1000.0
                    ),
                    "text": normalized["text"],
                    "tokens": normalized["tokens"],
                    "decode_ms": normalized["decode_ms"],
                    "final": normalized["final"],
                    "native": normalized["native"],
                    "native_fields_present": normalized["native_fields_present"],
                    "native_extra": normalized["native_extra"],
                    "language_hints": normalized["language_hints"],
                    "policy": None,
                    "native_commit": native_commit,
                    "timing": self._timing_block(
                        t0=t0,
                        scheduled_t=scheduled,
                        call_start=call_start,
                        call_end=call_end,
                        prefix_samples=fed,
                        arrived_before=arrived,
                        arrived_after=self._arrived(call_end, t0, fixture),
                        fixture=fixture,
                    ),
                }
            )

            if call_end >= audio_end_t - 1e-12:
                pending_coalesced = list(range(selected + 1, last_tick + 1))
                break
            latest = self._latest_eligible_tick(
                call_end, t0, last_tick, fixture, cfg.feed_chunk_ms
            )
            if latest > selected:
                events[-1]["coalesced_ticks"] = list(range(selected + 1, latest))
                events[-1]["next_selected_tick"] = latest
                selected = latest
            else:
                selected += 1

        self.clock.sleep_until(audio_end_t)
        now = self.clock.now()
        arrived = self._arrived(now, t0, fixture)
        remaining = fixture.samples[fed:arrived]
        call_start = now
        result = self._feed_native_final(remaining)
        call_end = self.clock.now()
        normalized = self._normalize_result(result)
        fed_before = fed
        fed = arrived
        native_commit = self._track_native_commit(
            tracker, normalized, event_index=len(events)
        )
        if normalized["native"]["display_text"] is not None:
            display_text = normalized["native"]["display_text"]
        elif normalized["native"]["tentative_text"] is not None:
            display_text = normalized["native"]["tentative_text"]
        if normalized["native"]["tentative_text"] is not None:
            tentative_text = normalized["native"]["tentative_text"]

        if "final_text" in normalized["native_fields_present"]:
            final_text = normalized["native"]["final_text"] or ""
            final_text_source = "result.final_text"
            if normalized["native"]["final_text"] is None:
                final_text = normalized["text"]
                final_text_source = "result.text (final_text null)"
        else:
            final_text = normalized["text"]
            final_text_source = "result.text (final_text not exposed)"
        final_event_index = len(events)
        finalization = tracker.finalize(final_text, event_index=final_event_index)
        events.append(
            {
                "event_index": final_event_index,
                "kind": "final",
                "selected_tick": None,
                "completed_tick": None,
                "coalesced_ticks": pending_coalesced,
                "next_selected_tick": None,
                "chunk_samples": len(remaining),
                "fed_before_samples": fed_before,
                "fed_after_samples": fed,
                "nominal_chunk_ms": cfg.feed_chunk_ms,
                "effective_chunk_ms": _round3(len(remaining) / sample_rate * 1000.0),
                "text": normalized["text"],
                "tokens": normalized["tokens"],
                "decode_ms": normalized["decode_ms"],
                "final": True,
                "native": normalized["native"],
                "native_fields_present": normalized["native_fields_present"],
                "native_extra": normalized["native_extra"],
                "language_hints": normalized["language_hints"],
                "policy": None,
                "native_commit": native_commit,
                "finalization": {
                    "final_text_source": final_text_source,
                    "stable_text": finalization["stable_text"],
                    "final_correction": finalization["final_correction"],
                },
                "timing": self._timing_block(
                    t0=t0,
                    scheduled_t=audio_end_t,
                    call_start=call_start,
                    call_end=call_end,
                    prefix_samples=fed,
                    arrived_before=arrived,
                    arrived_after=arrived,
                    fixture=fixture,
                ),
            }
        )

        return {
            "events": events,
            "final_text": final_text,
            "stable_text": finalization["stable_text"] or None,
            "display_text": display_text,
            "tentative_text": tentative_text,
            "stable_history": tracker.history,
            "conflicts": tracker.conflicts,
            "final_correction": finalization["final_correction"],
            "native_final_text_source": final_text_source,
            "arm_settings": {
                "feed_chunk_ms": cfg.feed_chunk_ms,
                "att_context_right_frames": cfg.right_context_frames,
                "commit_policy": cfg.commit_policy,
                "native_agreement_n": cfg.agreement_n,
                "max_window_ms": cfg.max_window_ms,
                "window_mode": cfg.window_mode,
            },
        }

    def _feed_native_final(self, remaining: Any) -> Any:
        """Final feed; an empty final flush is the defensive no-audio-remains path."""
        if len(remaining) > 0:
            return self._invoke("feed_final", self.engine.feed, remaining, final=True)
        return self._invoke("feed_final_flush", self.engine.feed, [], final=True)

    def _track_native_commit(
        self, tracker: policy.NativeCommitTracker, normalized: dict, *, event_index: int
    ) -> dict | None:
        if "committed_text" not in normalized["native_fields_present"]:
            return None
        committed = normalized["native"]["committed_text"]
        if committed is None:
            return None
        return tracker.update(committed, event_index=event_index)

    # -- trial builders ------------------------------------------------

    def _engine_info(self) -> dict | None:
        return _read_engine_info(self.engine)

    def _native_stream_exposure(self, info: dict | None) -> dict:
        requested = self.config.right_context_frames

        def first(*values: Any) -> Any:
            for value in values:
                if value is not None:
                    return value
            return None

        if not isinstance(info, dict):
            return {
                "requested": sanitize_metadata(requested),
                "engine_requested": None,
                "engine_requested_matches_runner_request": None,
                "applied": None,
                "applied_equals_requested": None,
                "accepted": None,
                "applied_context_status": "unavailable_not_inferred",
                "applied_context_source": None,
                "att_context_reason": None,
                "accepted_evidence": None,
                "adapter_default": None,
                "adapter_default_is_model_default": None,
                "adapter_default_evidence": None,
                "documented_model_default": DOCUMENTED_MODEL_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES,
                "exposed_model_default": None,
                "requested_equals_adapter_default": None,
                "requested_equals_documented_model_default": (
                    requested == DOCUMENTED_MODEL_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES
                ),
                "stream_contract": None,
                "capabilities": None,
                "source": "engine.info unavailable or not exposed",
                "note": (
                    "requested context is never treated as applied context; "
                    "applied and accepted are engine-reported values or null."
                ),
            }

        native = info.get("native_stream")
        native = native if isinstance(native, dict) else {}
        contract = info.get("stream_contract")
        contract = contract if isinstance(contract, dict) else {}
        nested_contract = native.get("stream_contract")
        if isinstance(nested_contract, dict):
            contract = {**nested_contract, **contract}

        applied = first(
            native.get("att_context_right_frames_applied"),
            native.get("applied_att_context_right_frames"),
            contract.get("att_context_right_frames_applied"),
            contract.get("applied_att_context_right_frames"),
            info.get("att_context_right_frames_applied"),
        )
        accepted = first(
            native.get("att_context_right_frames_accepted"),
            contract.get("att_context_right_frames_accepted"),
            info.get("att_context_right_frames_accepted"),
        )
        engine_requested = first(
            native.get("att_context_right_frames_requested"),
            contract.get("att_context_right_frames_requested"),
            info.get("att_context_right_frames_requested"),
        )
        applied_source = first(
            native.get("applied_context_source"),
            contract.get("applied_context_source"),
            info.get("applied_context_source"),
        )
        accepted_evidence = first(
            native.get("accepted_evidence"),
            contract.get("accepted_evidence"),
            info.get("accepted_evidence"),
        )
        reason = first(
            native.get("att_context_reason"),
            contract.get("att_context_reason"),
            info.get("att_context_reason"),
        )
        adapter_default = first(
            contract.get("att_context_right_frames_default"),
            native.get("att_context_right_frames_default"),
            info.get("att_context_right_frames_default"),
        )
        adapter_default_is_model_default = first(
            contract.get("att_context_right_frames_default_is_model_default"),
            info.get("att_context_right_frames_default_is_model_default"),
        )
        adapter_default_evidence = first(
            contract.get("att_context_right_frames_default_evidence"),
            info.get("att_context_right_frames_default_evidence"),
        )
        exposed_model_default = first(
            native.get("model_default_att_context_right_frames"),
            native.get("att_context_right_frames_model_default"),
            contract.get("model_default_att_context_right_frames"),
            contract.get("att_context_right_frames_model_default"),
            info.get("model_default_att_context_right_frames"),
        )
        exposed = (
            applied is not None
            or accepted is not None
            or adapter_default is not None
            or exposed_model_default is not None
            or reason is not None
        )
        return {
            "requested": sanitize_metadata(requested),
            "engine_requested": sanitize_metadata(engine_requested),
            "engine_requested_matches_runner_request": (
                None if engine_requested is None else engine_requested == requested
            ),
            "applied": sanitize_metadata(applied),
            "applied_equals_requested": (
                None if applied is None else applied == requested
            ),
            "accepted": sanitize_metadata(accepted),
            "applied_context_status": (
                "engine_reported" if applied is not None else "unavailable_not_inferred"
            ),
            "applied_context_source": sanitize_metadata(applied_source),
            "att_context_reason": sanitize_metadata(reason),
            "accepted_evidence": sanitize_metadata(accepted_evidence),
            "adapter_default": sanitize_metadata(adapter_default),
            "adapter_default_is_model_default": sanitize_metadata(
                adapter_default_is_model_default
            ),
            "adapter_default_evidence": sanitize_metadata(adapter_default_evidence),
            "documented_model_default": DOCUMENTED_MODEL_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES,
            "exposed_model_default": sanitize_metadata(exposed_model_default),
            "requested_equals_adapter_default": (
                None
                if adapter_default is None
                else requested == adapter_default
            ),
            "requested_equals_documented_model_default": (
                requested == DOCUMENTED_MODEL_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES
            ),
            "stream_contract": sanitize_metadata(contract) if contract else None,
            "capabilities": sanitize_metadata(info.get("capabilities")),
            "source": "engine.info" if exposed else "not_exposed_by_engine",
            "note": (
                "requested context is never treated as applied context; applied "
                "is only the engine-reported applied value, accepted is the "
                "engine-reported accepted value (nullable), and the adapter API "
                "default is separate from the documented model default."
            ),
        }

    def _language_metadata(
        self, fixture: Fixture, info: dict | None, events: Sequence[dict]
    ) -> dict:
        requested, source = self._language_for(fixture)
        hint_names = (
            "language",
            "requested_language",
            "resolved_language",
            "detected_language",
            "lid_supported",
        )
        hints: dict[str, Any] = {}
        for name in hint_names:
            hints[name] = None
            for event in events:
                event_hints = event.get("language_hints") or {}
                if isinstance(event_hints, dict) and event_hints.get(name) is not None:
                    hints[name] = event_hints[name]
                    break

        resolved = hints["resolved_language"]
        detected = hints["detected_language"]
        lid_supported = hints["lid_supported"]
        languages = None
        if isinstance(info, dict):
            if resolved is None:
                resolved = info.get("resolved_language")
            if detected is None:
                detected = info.get("detected_language")
            capabilities = info.get("capabilities")
            if isinstance(capabilities, dict):
                if lid_supported is None:
                    lid_supported = capabilities.get("lid")
                languages = capabilities.get("languages")
        return {
            "requested": requested,
            "requested_source": source,
            "engine_default": self.config.engine_language,
            "backend_requested_hint": sanitize_metadata(hints["requested_language"]),
            "backend_language_hint": sanitize_metadata(hints["language"]),
            "resolved": sanitize_metadata(resolved),
            "detected": sanitize_metadata(detected),
            "lid_supported": sanitize_metadata(lid_supported),
            "available_languages": sanitize_metadata(languages),
            "note": (
                "fixture.asr_language (including the documented 'auto' sentinel) "
                "is passed through unchanged to the engine; the runner never "
                "forces a first language prompt or reloads the model. "
                "resolved/detected are null unless the engine exposes them."
            ),
        }

    def _build_ok_trial(
        self,
        fixture: Fixture,
        *,
        phase: str,
        trial_index: int,
        repeat_index: int,
        trial_id: str,
        t0: float,
        bundle: dict,
        setup: dict,
    ) -> dict:
        sample_rate = fixture.sample_rate
        sample_count = len(fixture.samples)
        audio_end_ms = _round3(sample_count / sample_rate * 1000.0)
        info = self._engine_info()
        final_text = bundle["final_text"]
        stable_text = bundle["stable_text"]
        events = bundle["events"]
        debug_wer = metrics.wer(fixture.reference_text, final_text)
        stable_wer = (
            metrics.wer(fixture.reference_text, stable_text)
            if isinstance(stable_text, str) and stable_text.strip()
            else None
        )
        context = context_metadata(
            self.config.arm, self.config.right_context_frames
        )
        replay = {
            "clock_mode": self.config.clock_mode,
            "mode": (
                "real_paced_replay"
                if self.config.clock_mode == "real"
                else "simulated_fake_clock"
            ),
            "arm": self.config.arm,
            "sample_rate": sample_rate,
            "audio_end_ms": audio_end_ms,
            "arrival_model": (
                "sample i becomes available at replay_start + (i+1)/sample_rate; "
                "only arrived audio is decoded"
            ),
            "replay_origin_note": (
                "replay_start t0 is one sample period before the first fixture "
                "sample becomes available; first_partial_ms/first_stable_ms are "
                "conservatively high by 1/sample_rate (0.0625 ms at 16 kHz). "
                "The origin convention is retained for metric stability."
            ),
            "future_audio_guard": (
                "prefix frozen before each call; frozen_prefix_samples <= "
                "arrived_samples for every event"
            ),
            "context": context,
            "stream_latency_setting": context["stream_latency_setting"],
            "settings": sanitize_metadata(bundle.get("arm_settings") or {}),
        }
        texts = {
            "final_raw": final_text,
            "final_normalized": metrics.normalize_text(final_text),
            "stable_raw": stable_text,
            "stable_normalized": (
                metrics.normalize_text(stable_text)
                if isinstance(stable_text, str) and stable_text
                else None
            ),
            "display_text": bundle.get("display_text"),
            "tentative_text": bundle.get("tentative_text"),
        }
        native_start = setup.get("native_start")
        trial = {
            "trial_id": trial_id,
            "trial_index": trial_index,
            "phase": phase,
            "repeat_index": repeat_index,
            "fixture_id": fixture.id,
            "arm": self.config.arm,
            "clock_mode": self.config.clock_mode,
            "status": "ok",
            "fixture": fixture.identity(),
            "audio": {
                "sample_rate": sample_rate,
                "samples": sample_count,
                "duration_s": fixture.duration_s,
                "duration_ms": audio_end_ms,
                "audio_end_ms": audio_end_ms,
            },
            "language": self._language_metadata(fixture, info, events),
            "replay": replay,
            "events": events,
            "texts": texts,
            "stable_history": bundle.get("stable_history") or [],
            "conflicts": bundle.get("conflicts") or [],
            "final_correction": bundle.get("final_correction"),
            "native_final_text_source": bundle.get("native_final_text_source"),
            "wer": debug_wer,
            "stable_wer": stable_wer,
            "timings": metrics.compute_timings(
                events,
                audio_end_ms=audio_end_ms,
                arm=self.config.arm,
                clock_mode=self.config.clock_mode,
            ),
            "engine": {
                "info": sanitize_metadata(info),
                "native_stream": (
                    {
                        "requested": sanitize_metadata(
                            native_start.get("requested") if native_start else None
                        ),
                        "start_wall_ms": (
                            native_start.get("call_wall_ms") if native_start else None
                        ),
                        "start_return": (
                            native_start.get("returned") if native_start else None
                        ),
                        "exposed": self._native_stream_exposure(info),
                    }
                    if self.config.arm == "native-stream"
                    else None
                ),
            },
        }
        return trial

    def _non_ok_trial(
        self,
        fixture: Fixture,
        *,
        phase: str,
        trial_index: int,
        repeat_index: int,
        trial_id: str,
        status: str,
        error_type: str,
        message: str,
        fatal_stream_state: bool,
    ) -> dict:
        sample_rate = fixture.sample_rate
        sample_count = len(fixture.samples)
        audio_end_ms = _round3(sample_count / sample_rate * 1000.0)
        context = context_metadata(
            self.config.arm, self.config.right_context_frames
        )
        return {
            "trial_id": trial_id,
            "trial_index": trial_index,
            "phase": phase,
            "repeat_index": repeat_index,
            "fixture_id": fixture.id,
            "arm": self.config.arm,
            "clock_mode": self.config.clock_mode,
            "status": status,
            "replay": {
                "clock_mode": self.config.clock_mode,
                "arm": self.config.arm,
                "context": context,
                "stream_latency_setting": context["stream_latency_setting"],
            },
            "fixture": fixture.identity(),
            "audio": {
                "sample_rate": sample_rate,
                "samples": sample_count,
                "duration_s": fixture.duration_s,
                "duration_ms": audio_end_ms,
                "audio_end_ms": audio_end_ms,
            },
            "error": {"type": error_type, "message": message},
            "fatal_stream_state": bool(fatal_stream_state),
            "events": [],
            "texts": None,
            "stable_history": [],
            "conflicts": [],
            "final_correction": None,
            "wer": None,
            "stable_wer": None,
            "timings": None,
        }


def _sanitize_tokens(tokens: Any) -> list[dict]:
    if not isinstance(tokens, list):
        return []
    cleaned: list[dict] = []
    for row in tokens:
        if not isinstance(row, dict):
            continue
        item: dict = {}
        for key, value in row.items():
            if isinstance(value, float):
                item[str(key)] = value if math.isfinite(value) else None
            elif value is None or isinstance(value, (bool, int, str)):
                item[str(key)] = value
            elif isinstance(value, (list, tuple, dict)):
                item[str(key)] = sanitize_metadata(value)
            else:
                item[str(key)] = str(value)
        cleaned.append(item)
    return cleaned


# ---------------------------------------------------------------------------
# Experiment planning
# ---------------------------------------------------------------------------


def execute_plan(
    manifest: Manifest,
    runner: ReplayRunner,
    *,
    repeats: int,
    warmup: int,
) -> list[dict]:
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
        raise ValueError("repeats must be a positive integer")
    if isinstance(warmup, bool) or not isinstance(warmup, int) or warmup < 0:
        raise ValueError("warmup must be a nonnegative integer")
    trials: list[dict] = []
    trial_index = 0
    abort_reason: str | None = None
    for phase, count in (("warmup", warmup), ("measured", repeats)):
        for repeat in range(count):
            for fixture in manifest.fixtures:
                if abort_reason is not None:
                    trial = runner.non_ok_trial(
                        fixture,
                        phase=phase,
                        trial_index=trial_index,
                        repeat_index=repeat,
                        status="skipped",
                        reason=abort_reason,
                    )
                else:
                    trial = runner.run(
                        fixture,
                        phase=phase,
                        trial_index=trial_index,
                        repeat_index=repeat,
                    )
                    if trial.get("status") == "error" and trial.get(
                        "fatal_stream_state"
                    ):
                        abort_reason = (
                            "a previous native-stream trial failed; stream state "
                            "may be poisoned, later trials were not started"
                        )
                trials.append(trial)
                trial_index += 1
    return trials


# ---------------------------------------------------------------------------
# Result document and output
# ---------------------------------------------------------------------------


@dataclass
class RunMetadata:
    arm: str
    clock_mode: str
    replay: dict
    model: dict
    library: dict | None = None
    engine: dict | None = None
    build: dict | None = None
    load: dict | None = None
    invocation: dict | None = None
    host: dict | None = None
    git: dict | None = None
    sources: dict | None = None
    generated_at_utc: str | None = None
    limitations: list[str] | None = None


DEFAULT_LIMITATIONS = [
    "Tiny-fixture feasibility evidence only; not a model leaderboard and not an acceptance threshold.",
    "Oracle fixture segment boundaries are not a tested VAD.",
    "No independent gold word timings exist: word-end/display latency is unsupported/null, never inferred from model token timestamps.",
    "call_wall_ms includes validation/transport/native compute; it is not pure GPU decode time. Native decode_ms is nullable; zero, negative and nonfinite values are unknown and never zero-filled.",
    "Default fixtures mix natural FLEURS material with derived/synthetic assemblies (repeated natural audio and EN→ES concatenation). Endpoint decode splits derived assemblies at oracle segment boundaries and does not exercise within-call or mid-sentence language switching; separate natural-versus-derived tables when interpreting results.",
    "Rolling/long-call windows are unsupported: fixtures above the configured max window are rejected rather than silently truncated.",
    "Fake-clock trials populate simulated timing fields only and are not live-call evidence.",
    "Firefox/capture, live calls and interview participation are outside this runner.",
]


def _context_limitation(replay: Any) -> str:
    """Derive the context/lookahead limitation from effective settings."""
    if isinstance(replay, dict):
        context = replay.get("context")
        if isinstance(context, dict):
            limitation = context.get("limitation")
            if isinstance(limitation, str) and limitation.strip():
                return limitation
    return (
        "Native-vs-offline right-context/lookahead is not recorded in this "
        "result; applied native context is engine-reported only and is never "
        "inferred from the requested value."
    )


def _collect_document_fixtures(trials: Sequence[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for trial in trials:
        fixture = trial.get("fixture")
        if isinstance(fixture, dict) and fixture.get("id") not in seen:
            seen[fixture["id"]] = fixture
    return list(seen.values())


def aggregate_trials(trials: Sequence[dict]) -> dict:
    measured = [trial for trial in trials if trial.get("phase") == "measured"]
    warmup = [trial for trial in trials if trial.get("phase") == "warmup"]
    ok = [trial for trial in measured if trial.get("status") == "ok"]
    failed = [trial for trial in measured if trial.get("status") == "error"]
    skipped = [trial for trial in measured if trial.get("status") == "skipped"]

    def micro(subset: Sequence[dict]) -> dict:
        return metrics.micro_aggregate([trial.get("wer") for trial in subset])

    by_fixture: dict[str, dict] = {}
    fixture_ids = list(dict.fromkeys(trial.get("fixture_id") for trial in measured))
    for fixture_id in fixture_ids:
        subset = [trial for trial in measured if trial.get("fixture_id") == fixture_id]
        subset_ok = [trial for trial in subset if trial.get("status") == "ok"]
        by_fixture[fixture_id] = {
            "trials": len(subset),
            "ok_trials": len(subset_ok),
            "wer": micro(subset_ok),
        }

    return {
        "phase": "measured",
        "measured_trials": len(measured),
        "ok_trials": len(ok),
        "failed_trials": len(failed),
        "skipped_trials": len(skipped),
        "warmup_trials": len(warmup),
        "warmup_excluded_from_aggregates": True,
        "wer": micro(ok),
        "by_fixture": by_fixture,
        "timings_note": (
            "Timing metrics are per-trial and clock-labelled; fake-clock values "
            "are simulated and do not populate measured fields. No cross-trial "
            "latency average is presented as a live-call promise."
        ),
    }


def build_results_document(
    metadata: RunMetadata, trials: Sequence[dict]
) -> dict:
    if not isinstance(metadata, RunMetadata):
        raise TypeError("metadata must be a RunMetadata instance")
    trial_list = list(trials)
    limitations = list(metadata.limitations or DEFAULT_LIMITATIONS)
    context_limitation = _context_limitation(metadata.replay)
    if context_limitation and context_limitation not in limitations:
        limitations.append(context_limitation)
    document = {
        "schema_version": 1,
        "kind": "asr_spike_trial_results",
        "generated_at_utc": metadata.generated_at_utc or _utc_now(),
        "arm": metadata.arm,
        "clock_mode": metadata.clock_mode,
        "replay": sanitize_metadata(metadata.replay),
        "git": sanitize_metadata(metadata.git),
        "sources": sanitize_metadata(metadata.sources),
        "host": sanitize_metadata(metadata.host),
        "model": sanitize_metadata(metadata.model),
        "library": sanitize_metadata(metadata.library),
        "engine": sanitize_metadata(metadata.engine),
        "build": sanitize_metadata(metadata.build),
        "load": sanitize_metadata(metadata.load),
        "invocation": sanitize_metadata(metadata.invocation),
        "fixtures": _collect_document_fixtures(trial_list),
        "trials": trial_list,
        "aggregates": aggregate_trials(trial_list),
        "metric_definitions": copy.deepcopy(metrics.DEFINITIONS),
        "limitations": limitations,
    }
    # Fail at construction if any nonfinite value leaked; write also uses
    # allow_nan=False and an atomic replace.
    json.dumps(document, allow_nan=False, ensure_ascii=False)
    return document


def write_results_atomic(
    path: Path, document: dict, *, allow_overwrite: bool = False
) -> None:
    target = Path(path)
    if target.exists() and not allow_overwrite:
        raise OutputCollisionError(
            f"output already exists: {target.name}; pass explicit overwrite to replace it"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=target.name + ".", suffix=".tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                document,
                handle,
                ensure_ascii=False,
                allow_nan=False,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        if target.exists() and not allow_overwrite:
            raise OutputCollisionError(
                f"output appeared while writing: {target.name}; refusing to replace it"
            )
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Fingerprints and CLI
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def collect_sources() -> dict:
    sources: dict[str, dict] = {}
    for name in (
        "run.py",
        "policy.py",
        "metrics.py",
        "backend.py",
        "engine.lock.json",
        "fixtures/manifest_tools.py",
    ):
        path = SPIKE_ROOT / name
        if path.is_file():
            sources[name] = {
                "sha256": file_sha256(path),
                "size_bytes": path.stat().st_size,
            }
    return sources


def collect_build_metadata() -> dict:
    """Summarize the pinned engine lock without copying opaque cache paths."""
    path = SPIKE_ROOT / "engine.lock.json"
    if not path.is_file():
        return {"source": "engine.lock.json", "available": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "source": "engine.lock.json",
            "available": False,
            "error": f"unreadable lock: {type(exc).__name__}: {_redact(exc)}",
        }
    artifact = data.get("artifact") if isinstance(data, dict) else None
    import_check = artifact.get("import_check") if isinstance(artifact, dict) else None
    return {
        "source": "engine.lock.json",
        "available": True,
        "lock_sha256": file_sha256(path),
        "engine": data.get("engine") if isinstance(data, dict) else None,
        "artifact_sha256": (
            artifact.get("sha256") if isinstance(artifact, dict) else None
        ),
        "artifact_backends": (
            import_check.get("backends") if isinstance(import_check, dict) else None
        ),
        "build": data.get("build") if isinstance(data, dict) else None,
        "runtime": data.get("runtime") if isinstance(data, dict) else None,
        "source_verification": (
            data.get("source_verification") if isinstance(data, dict) else None
        ),
    }


def collect_git() -> dict:
    def git(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(SPIKE_ROOT), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

    try:
        commit = git("rev-parse", "HEAD")
        branch = git("rev-parse", "--abbrev-ref", "HEAD")
        status = git("status", "--porcelain", "--untracked-files=no")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "commit": None,
            "branch": None,
            "dirty_tracked": None,
            "source": f"git unavailable: {type(exc).__name__}",
        }
    return {
        "commit": commit.stdout.strip() if commit.returncode == 0 else None,
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "dirty_tracked": bool(status.stdout.strip()) if status.returncode == 0 else None,
        "source": "git",
    }


def collect_host_info() -> dict:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or None,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "cpu_count": os.cpu_count(),
        "note": "hostname, usernames, home directories and absolute cache paths are omitted",
    }


def _normalize_supplied_sha(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    if not _SHA256_RE.fullmatch(value):
        raise SpikeError(f"{label} must be a 64-character hexadecimal SHA-256")
    return value.lower()


def describe_file(path: str, *, supplied_sha256: str | None = None) -> dict:
    candidate = Path(path).expanduser()
    if not candidate.is_file():
        raise SpikeError(f"file not found: {candidate.name}")
    supplied = _normalize_supplied_sha(supplied_sha256, "supplied sha256")
    sha = supplied or file_sha256(candidate)
    try:
        relative = candidate.resolve().relative_to(SPIKE_ROOT).as_posix()
        scope = "spike_relative"
    except ValueError:
        relative = None
        scope = "external_redacted"
    return {
        "basename": candidate.name,
        "sha256": sha,
        "size_bytes": candidate.stat().st_size,
        "scope": scope,
        "spike_relative_path": relative,
        "hash_source": "supplied" if supplied else "computed_sha256",
    }


def _load_backend() -> Any:
    try:
        import backend  # type: ignore
    except Exception as exc:
        raise SpikeError(
            "cannot import backend.py; build/inspect the native adapter first: "
            f"{type(exc).__name__}: {_redact(exc)}"
        ) from exc
    return backend


def _read_engine_info(engine: Any) -> dict | None:
    try:
        info = getattr(engine, "info", None)
    except Exception as exc:
        return {"error": _redact(f"{type(exc).__name__}: {exc}")}
    return info if isinstance(info, dict) else None


def create_engine(args: argparse.Namespace) -> tuple[Any, dict, dict | None]:
    backend = _load_backend()
    model_path = Path(args.model).expanduser()
    if not model_path.is_file():
        raise SpikeError(f"model file not found: {model_path.name}")
    kwargs: dict = {
        "language": args.language or "auto",
        "threads": args.threads,
        "use_gpu": not args.cpu,
    }
    if args.library:
        library_path = Path(args.library).expanduser()
        if not library_path.is_file():
            raise SpikeError(f"library file not found: {library_path.name}")
        kwargs["library_path"] = str(library_path)
    started = time.monotonic()
    try:
        engine = backend.Engine(str(model_path), **kwargs)
    except Exception as exc:
        raise SpikeError(
            f"engine construction failed: {type(exc).__name__}: {_redact(exc)}"
        ) from exc
    constructor_wall_ms = _round_ms_from_seconds(time.monotonic() - started)
    info = _read_engine_info(engine)
    load_info = {
        "constructor_wall_ms": constructor_wall_ms,
        "constructor_wall_clock": "real_monotonic_measured",
        "constructor_scope": (
            "Engine construction/model load; model reuse across fixtures and "
            "trials is intentional; decode calls are measured separately"
        ),
        "engine_reported_load_ms": _finite_or_none(
            (info or {}).get("load_ms") if isinstance(info, dict) else None
        ),
        "engine_reported_load_ms_source": (
            "engine.info.load_ms"
            if isinstance(info, dict) and info.get("load_ms") is not None
            else "unknown"
        ),
        "warmup_trials": None,
    }
    return engine, load_info, info


def check_arm_capabilities(info: dict | None, arm: str) -> dict | None:
    if arm not in ARMS:
        raise ValueError(f"unsupported arm {arm!r}")
    flag = "native_stream" if arm == "native-stream" else "batch"
    if not isinstance(info, dict):
        return None
    capabilities = info.get("capabilities")
    if not isinstance(capabilities, dict):
        return None
    value = capabilities.get(flag)
    if value is False:
        raise CapabilityError(
            f"engine explicitly reports capability {flag!r}=false; arm {arm!r} "
            "cannot run and will not silently fall back"
        )
    return {"required": flag, "reported": value, "enforced": value is False}


def sanitize_argv(argv: Sequence[str]) -> list[str]:
    path_flags = {"--model", "--library", "--manifest", "--output"}
    output: list[str] = []
    redact_next = False
    for token in argv:
        if redact_next:
            output.append(_public_path(token))
            redact_next = False
            continue
        if token in path_flags:
            output.append(token)
            redact_next = True
            continue
        matched = False
        for flag in path_flags:
            prefix = flag + "="
            if token.startswith(prefix):
                output.append(prefix + _public_path(token[len(prefix) :]))
                matched = True
                break
        if matched:
            continue
        output.append(_redact(token))
    return output


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def _nonnegative_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be nonnegative")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Paced replay for endpoint, growing-prefix hybrid and native-stream "
            "transcription arms. Only arrived audio is decoded; result timings "
            "are replay-relative and labelled by clock source."
        )
    )
    parser.add_argument("--model", required=True, help="path to the cached model file")
    parser.add_argument(
        "--library",
        default=None,
        help="optional native helper library path (project-local discovery when omitted)",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="fixture manifest path (default: <spike-root>/fixtures/manifest.json)",
    )
    parser.add_argument("--arm", choices=ARMS, required=True, help="decoding arm")
    parser.add_argument("--output", required=True, help="strict JSON result path")
    parser.add_argument(
        "--repeats",
        type=_positive_int,
        default=2,
        help="measured repeats per fixture",
    )
    parser.add_argument(
        "--warmup",
        type=_nonnegative_int,
        default=1,
        help="warmup passes over selected fixtures, excluded from aggregates",
    )
    parser.add_argument(
        "--fixture",
        action="append",
        default=None,
        help="fixture id to run (repeatable; default: all selected fixtures)",
    )
    parser.add_argument(
        "--language",
        default="auto",
        help="engine constructor language/autodetect hint",
    )
    parser.add_argument(
        "--asr-language",
        default=None,
        help="per-fixture ASR language prompt override (no model reload)",
    )
    parser.add_argument(
        "--partial-interval-ms",
        type=_positive_int,
        default=500,
        help="hybrid partial scheduled-tick interval in audio-clock ms",
    )
    parser.add_argument(
        "--max-window-ms",
        type=_positive_int,
        default=20000,
        help=(
            "maximum fixed-start window; selected clips above it are rejected, "
            "not rolled. The shared manifest validator independently caps "
            "default fixtures at 20 s; this option can be stricter, not looser"
        ),
    )
    parser.add_argument(
        "--feed-chunk-ms",
        type=_positive_int,
        default=1120,
        help="native caller feed cadence in ms; not a native C API field",
    )
    parser.add_argument(
        "--right-context-frames",
        type=_nonnegative_int,
        default=NATIVE_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES,
        help=(
            "native cache-aware right context in encoder frames. The binding "
            "native comparison default is R=3; R=13 is an explicit control, not "
            "the default. The pinned adapter API default is 3 and the documented "
            "model default is 13. The value is passed through; applied context "
            "is engine-reported only and rejected by the engine if unsupported"
        ),
    )
    parser.add_argument(
        "--commit-policy",
        default="stable-prefix",
        help="native commit policy (runner hybrid uses word-level LA-2)",
    )
    parser.add_argument(
        "--agreement-n",
        type=_positive_int,
        default=2,
        help="native stable-prefix agreement count; runner hybrid is fixed LA-2",
    )
    parser.add_argument(
        "--clock-mode",
        choices=CLOCK_MODES,
        default="real",
        help=(
            "real paced replay from time.monotonic; fake is reserved for "
            "deterministic fake-engine tests and is rejected by the CLI"
        ),
    )
    parser.add_argument(
        "--window-mode",
        choices=("fixed-start",),
        default="fixed-start",
        help="fixed-start growing prefix only; rolling windows are unsupported",
    )
    parser.add_argument("--threads", type=_positive_int, default=4, help="engine threads")
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="construct the engine with use_gpu=False",
    )
    parser.add_argument(
        "--allow-overwrite",
        action="store_true",
        help="replace an existing output file explicitly",
    )
    parser.add_argument(
        "--model-sha256",
        default=None,
        help="precomputed model SHA-256 (avoids re-hashing a large cached model)",
    )
    parser.add_argument(
        "--library-sha256",
        default=None,
        help="precomputed helper library SHA-256",
    )
    return parser


def _effective_settings(
    args: argparse.Namespace,
    manifest: Manifest,
    output: Path,
) -> dict:
    context = context_metadata(args.arm, args.right_context_frames)
    return {
        "arm": args.arm,
        "manifest": {
            "path": _public_path(manifest.path),
            "sha256": manifest.sha256,
            "fixture_ids": [fixture.id for fixture in manifest.fixtures],
        },
        "output": _public_path(output),
        "repeats": args.repeats,
        "warmup": args.warmup,
        "partial_interval_ms": args.partial_interval_ms,
        "max_window_ms": args.max_window_ms,
        "feed_chunk_ms": args.feed_chunk_ms,
        "right_context_frames": args.right_context_frames,
        "context": context,
        "stream_latency_setting": context["stream_latency_setting"],
        "commit_policy": args.commit_policy,
        "agreement_n": args.agreement_n,
        "language": args.language,
        "asr_language_override": args.asr_language,
        "clock_mode": args.clock_mode,
        "window_mode": args.window_mode,
        "threads": args.threads,
        "use_gpu": not args.cpu,
        "runner_local_agreement_n": (
            policy.AGREEMENT_N if args.arm == "hybrid" else None
        ),
        "native_commit_policy": (
            args.commit_policy if args.arm == "native-stream" else None
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    engine = None
    try:
        if args.clock_mode != "real":
            raise SpikeError(
                "fake clock mode is reserved for deterministic fake-engine "
                "tests; the CLI runs real-paced replay only"
            )
        manifest_path = (
            Path(args.manifest).expanduser()
            if args.manifest
            else SPIKE_ROOT / "fixtures" / "manifest.json"
        )
        output = Path(args.output).expanduser()
        if output.exists() and not args.allow_overwrite:
            raise OutputCollisionError(
                f"output already exists: {output.name}; pass --allow-overwrite"
            )

        manifest = load_manifest(
            manifest_path,
            spike_root=SPIKE_ROOT,
            max_window_ms=args.max_window_ms,
            only_ids=args.fixture,
        )
        config = ReplayConfig(
            arm=args.arm,
            clock_mode=args.clock_mode,
            partial_interval_ms=args.partial_interval_ms,
            feed_chunk_ms=args.feed_chunk_ms,
            max_window_ms=args.max_window_ms,
            right_context_frames=args.right_context_frames,
            commit_policy=args.commit_policy,
            agreement_n=args.agreement_n,
            engine_language=args.language or "auto",
            asr_language_override=args.asr_language,
            window_mode=args.window_mode,
        )

        model_info = describe_file(args.model, supplied_sha256=args.model_sha256)
        library_info = (
            describe_file(args.library, supplied_sha256=args.library_sha256)
            if args.library
            else None
        )
        engine, load_info, engine_info = create_engine(args)
        load_info["warmup_trials"] = args.warmup * len(manifest.fixtures)
        check_arm_capabilities(engine_info, args.arm)

        runner = ReplayRunner(engine, RealClock(), config)
        trials = execute_plan(
            manifest, runner, repeats=args.repeats, warmup=args.warmup
        )
        context = context_metadata(args.arm, args.right_context_frames)
        metadata = RunMetadata(
            arm=args.arm,
            clock_mode=args.clock_mode,
            replay={
                "mode": "real_paced_replay",
                "clock_source": "time.monotonic",
                "arrival_model": (
                    "sample i becomes available at replay_start + (i+1)/"
                    "sample_rate on a monotonic audio clock; only arrived "
                    "samples are decoded"
                ),
                "replay_origin_note": (
                    "replay_start t0 is one sample period before the first "
                    "fixture sample becomes available; first_partial_ms and "
                    "first_stable_ms are conservatively high by 1/sample_rate "
                    "(0.0625 ms at 16 kHz). The convention is retained for "
                    "metric stability."
                ),
                "context": context,
                "stream_latency_setting": context["stream_latency_setting"],
                "config": _effective_settings(args, manifest, output),
            },
            model=model_info,
            library=library_info,
            engine={"info": engine_info},
            build=collect_build_metadata(),
            load=load_info,
            invocation={
                "argv": sanitize_argv(
                    list(argv) if argv is not None else sys.argv[1:]
                ),
                "effective": _effective_settings(args, manifest, output),
            },
            host=collect_host_info(),
            git=collect_git(),
            sources=collect_sources(),
        )
        document = build_results_document(metadata, trials)
        write_results_atomic(
            output, document, allow_overwrite=args.allow_overwrite
        )
        ok = sum(1 for trial in trials if trial.get("status") == "ok")
        failed = sum(1 for trial in trials if trial.get("status") == "error")
        skipped = sum(1 for trial in trials if trial.get("status") == "skipped")
        summary = {
            "output": _public_path(output),
            "trials": len(trials),
            "ok": ok,
            "failed": failed,
            "skipped": skipped,
            "micro_wer": document["aggregates"]["wer"]["micro_wer"],
        }
        print(json.dumps(summary, ensure_ascii=False))
        return 0 if failed == 0 and skipped == 0 else 1
    except SpikeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
    finally:
        if engine is not None:
            try:
                engine.close()
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
