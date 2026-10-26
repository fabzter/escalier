"""Persistent transcription engine adapter for spike 001.

This module is the only Python surface the experiment runner uses for model
compute.  It wraps the pinned project's **official standard-library-only
ctypes binding** (``transcribe_cpp``) loaded directly from the pinned checkout
under ``.tools/``; nothing is pip-installed and nothing is built or downloaded
implicitly at construction time.

Contract highlights (see ``SPEC.md`` for the authoritative version):

* :class:`Engine` loads one model once and reuses it for batch calls and
  native streams.  Batch and stream sessions are separate and reused/reset.
* Samples are finite mono float PCM at exactly 16000 Hz.  Invalid values,
  rates, empty batch audio, and over-model-limit audio are rejected before a
  native call.
* Per-call/per-stream ``language`` overrides do not reload the model.  ``auto``
  maps to the native ``NULL`` autodetect sentinel; a region-qualified code such
  as ``es-US`` is reduced to a declared primary language (recorded as a
  mapping), otherwise the call fails with the available language list.
* ``text`` is the native cumulative ``full_text``.  On stream finalization
  ``final_text`` is the authoritative ``full_text`` snapshot even when native
  ``committed_text`` differs.  Token times are ``None`` when the model reports
  no timestamp kind; zero/unknown native timings become ``None`` rather than a
  fabricated zero.
* Unsupported native streaming raises :class:`UnsupportedCapability`; it never
  silently falls back to batch decoding.
* ``close()`` is idempotent, safe after failed calls, and releases an active
  stream's lease before closing sessions and the model.

The binding enforces one compute call at a time per model and one active
stream per model.  This adapter adds an engine-level re-entrant lock so its own
sessions are also used serially.
"""

from __future__ import annotations

import copy
import ctypes
import hashlib
import json
import math
import os
import sys
import threading
from array import array
from pathlib import Path

_SPIKE_ROOT = Path(__file__).resolve().parent
_LOCK_PATH = _SPIKE_ROOT / "engine.lock.json"
_BINDING_SRC = _SPIKE_ROOT / ".tools" / "transcribe.cpp" / "bindings" / "python" / "src"

#: Project-local discovery order.  Never consult PATH, site-packages, caches
#: outside this spike, or an implicit build/download.  ``native/`` is the
#: task-owned optional helper location; ``.tools/build`` is the pinned build.
_LIBRARY_CANDIDATES = (
    "native/libtranscribe.dylib",
    "native/libtranscribe.so",
    ".tools/build/src/libtranscribe.dylib",
    ".tools/build/src/libtranscribe.so",
    ".tools/build/bin/libtranscribe.dylib",
    ".tools/build/bin/libtranscribe.so",
    ".tools/build/lib/libtranscribe.dylib",
    ".tools/build/lib/libtranscribe.so",
    ".tools/install/lib/libtranscribe.dylib",
    ".tools/install/lib/libtranscribe.so",
    ".tools/lib/libtranscribe.dylib",
    ".tools/lib/libtranscribe.so",
)

_SAMPLE_RATE = 16000
_DEFAULT_FEED_CHUNK_MS = 1120
_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES = 3
_DEFAULT_COMMIT_POLICY = "stable-prefix"
_DEFAULT_AGREEMENT_N = 2
_SUPPORTED_COMMIT_POLICIES = {
    "stable-prefix": "stable_prefix",
    "stable_prefix": "stable_prefix",
    "auto": "auto",
    "on-finalize": "on_finalize",
    "on_finalize": "on_finalize",
}

#: The pinned engine source revision and its runtime binding identity are kept
#: in ``engine.lock.json``.  The build script duplicates nothing here.
_COMMIT_MIN_PREFIX = 7

_BINDING_MODULE = None
_BINDING_LIBRARY = None


class EngineError(RuntimeError):
    """Native/engine failure with the offending operation named."""


class EngineClosedError(EngineError):
    """A compute or stream operation was attempted after ``close()``."""


class EngineStateError(EngineError):
    """A lifecycle operation is invalid in the current stream/engine state."""


class UnsupportedCapability(EngineError):
    """The loaded model does not advertise a requested native capability."""


class AudioValidationError(ValueError):
    """Samples or sample-rate violate the finite mono 16 kHz contract."""


def _finite_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _nonnegative_int(value):
    if isinstance(value, bool):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if number >= 0 else None


def _text(value):
    return value if isinstance(value, str) else ""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _public_path(path: Path):
    """Return a publishable (relative-or-basename) path and its scope.

    Runtime results must not leak absolute home/cache paths.  Project-local
    resources are reported relative to the spike root; external paths keep only
    their file name and are labelled ``external``.
    """
    path = Path(path)
    try:
        resolved = path.resolve()
        return resolved.relative_to(_SPIKE_ROOT).as_posix(), "project"
    except (OSError, ValueError):
        return path.name, "external"


def discover_library(root: Path = _SPIKE_ROOT):
    """Find the built engine only inside the project's ignored trees."""
    root = Path(root)
    for relative in _LIBRARY_CANDIDATES:
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return None


def resolve_library_path(library_path, *, root: Path = _SPIKE_ROOT) -> Path:
    """Resolve an explicit library path or perform project-local discovery."""
    if library_path is not None:
        path = Path(library_path).expanduser()
        if path.is_dir():
            path = path / ("libtranscribe.dylib" if sys.platform == "darwin" else "libtranscribe.so")
        if not path.is_file():
            raise FileNotFoundError(f"transcribe library not found: {path}")
        return path.resolve()

    found = discover_library(root)
    if found is None:
        raise FileNotFoundError(
            "project-local libtranscribe was not found under "
            f"{root}. Build it with: python3 "
            "spikes/001-transcription/tools/build_engine.py"
        )
    return found.resolve()


def _load_lock(path: Path = _LOCK_PATH) -> dict:
    path = Path(path)
    if not path.is_file():
        raise EngineError(f"engine lock file is missing: {path}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lock = json.load(handle)
    except (OSError, ValueError) as exc:
        raise EngineError(f"cannot read engine lock {path}: {exc}") from exc
    if not isinstance(lock, dict) or lock.get("schema_version") != 1:
        raise EngineError(f"unsupported engine lock schema in {path}")
    engine = lock.get("engine")
    artifact = lock.get("artifact")
    if not isinstance(engine, dict) or not isinstance(artifact, dict):
        raise EngineError(f"engine lock {path} is missing engine/artifact records")
    for key in ("repository", "revision", "version"):
        if not isinstance(engine.get(key), str) or not engine[key].strip():
            raise EngineError(f"engine lock {path} is missing engine.{key}")
    if not isinstance(artifact.get("sha256"), str) or len(artifact["sha256"]) != 64:
        raise EngineError(f"engine lock {path} is missing artifact.sha256")
    return lock


def _commit_matches(actual: str, expected: str) -> bool:
    """Compare a native build commit with the pinned full revision.

    The pinned engine exposes ``native_commit()`` as a short (7-character) hash,
    so accept an unambiguous prefix in either direction.
    """
    actual = _text(actual).strip().lower()
    expected = _text(expected).strip().lower()
    if len(actual) < _COMMIT_MIN_PREFIX or len(expected) < _COMMIT_MIN_PREFIX:
        return False
    return actual == expected or expected.startswith(actual) or actual.startswith(expected)


def verify_native_identity(binding, lock: dict) -> dict:
    """Fail closed when the loaded native library is not the pinned build."""
    engine = lock["engine"]
    expected_version = str(engine["version"])
    expected_revision = str(engine["revision"])
    try:
        native_version = _text(binding.native_version())
        native_commit = _text(binding.native_commit())
    except Exception as exc:  # binding surface mismatch
        raise EngineError(f"cannot read native engine identity: {exc}") from exc

    if native_version != expected_version:
        raise EngineError(
            "native engine version mismatch: "
            f"lock expects {expected_version!r}, library reports {native_version!r}"
        )
    expected_binding_version = (engine.get("python_binding") or {}).get("version")
    if expected_binding_version:
        actual_binding_version = getattr(binding, "__version__", None)
        if actual_binding_version != expected_binding_version:
            raise EngineError(
                "Python binding version mismatch: lock expects "
                f"{expected_binding_version!r}, loaded binding reports "
                f"{actual_binding_version!r}"
            )
    if not _commit_matches(native_commit, expected_revision):
        raise EngineError(
            "native engine commit mismatch: "
            f"lock expects {expected_revision!r}, library reports {native_commit!r}"
        )
    return {
        "verified": True,
        "version": native_version,
        "native_commit": native_commit,
        "pinned_revision": expected_revision,
        "comparison": "exact_or_unambiguous_prefix",
    }


def verify_library_artifact(library: Path, lock: dict) -> dict:
    """Verify the on-disk library hash for the project-local pinned artifact."""
    library = Path(library).resolve()
    artifact = lock.get("artifact") or {}
    expected_sha = str(artifact.get("sha256") or "")
    expected_path = artifact.get("path")
    actual_sha = _sha256_file(library)
    record = {
        "sha256": actual_sha,
        "size_bytes": library.stat().st_size,
        "expected_sha256": expected_sha or None,
        "expected_path": expected_path,
        "verified": False,
    }
    if isinstance(expected_path, str):
        expected_abs = (_SPIKE_ROOT / expected_path).resolve()
        if expected_abs == library:
            if actual_sha != expected_sha:
                raise EngineError(
                    "transcribe library hash mismatch: lock records "
                    f"{expected_sha}, artifact is {actual_sha}. Rebuild with "
                    "tools/build_engine.py and update engine.lock.json."
                )
            record["verified"] = True
            record["reason"] = "project_artifact_hash_matches_lock"
            return record
        record["reason"] = "custom_library_path_not_the_locked_artifact"
        return record
    record["reason"] = "lock_has_no_artifact_path"
    return record


def _binding_source_matches(module, binding_src: Path) -> bool:
    """True only for the pinned checkout's ``transcribe_cpp/__init__.py``."""
    module_file = getattr(module, "__file__", None)
    if not module_file:
        return False
    try:
        resolved = Path(module_file).resolve()
        expected = (Path(binding_src) / "transcribe_cpp" / "__init__.py").resolve()
    except (OSError, TypeError, ValueError):
        return False
    return resolved == expected


def _drop_transcribe_modules() -> None:
    for name in [
        n for n in sys.modules if n == "transcribe_cpp" or n.startswith("transcribe_cpp.")
    ]:
        sys.modules.pop(name, None)


def _load_binding(library_path: Path):
    """Import the official binding against exactly the resolved library.

    The official package reads ``TRANSCRIBE_LIBRARY`` during import; set it only
    for that import and restore the caller's environment immediately.  A
    pre-imported module is accepted only when its Python source is the pinned
    checkout, not merely when it reports the same native dylib.
    """
    global _BINDING_MODULE, _BINDING_LIBRARY
    library_path = Path(library_path).resolve()

    if _BINDING_MODULE is not None:
        if _BINDING_LIBRARY != library_path:
            raise EngineError(
                "the official binding is already loaded against "
                f"{_BINDING_LIBRARY}; this process cannot switch native libraries"
            )
        return _BINDING_MODULE

    binding_src = _BINDING_SRC.resolve()
    if not (binding_src / "transcribe_cpp" / "__init__.py").is_file():
        raise EngineError(
            "official Python binding source is missing at "
            f"{binding_src}. Pin and build the engine first: python3 "
            "spikes/001-transcription/tools/build_engine.py"
        )

    existing = sys.modules.get("transcribe_cpp")
    if existing is not None and not _binding_source_matches(existing, binding_src):
        raise EngineError(
            "a pre-imported transcribe_cpp module is not the pinned binding "
            f"source under {binding_src}; refusing to use it even if it loads "
            "the same native library"
        )

    previous = os.environ.get("TRANSCRIBE_LIBRARY")
    os.environ["TRANSCRIBE_LIBRARY"] = str(library_path)
    inserted = False
    if str(binding_src) not in sys.path:
        sys.path.insert(0, str(binding_src))
        inserted = True
    try:
        import transcribe_cpp  # deliberate lazy native import
    except Exception as exc:
        _drop_transcribe_modules()
        raise EngineError(
            f"could not load the official transcribe.cpp binding: {exc}"
        ) from exc
    finally:
        if previous is None:
            os.environ.pop("TRANSCRIBE_LIBRARY", None)
        else:
            os.environ["TRANSCRIBE_LIBRARY"] = previous
        if inserted:
            try:
                sys.path.remove(str(binding_src))
            except ValueError:
                pass

    if not _binding_source_matches(transcribe_cpp, binding_src):
        _BINDING_MODULE = None
        _BINDING_LIBRARY = None
        _drop_transcribe_modules()
        raise EngineError(
            "the imported transcribe_cpp module is not the pinned binding "
            f"source under {binding_src}"
        )

    _BINDING_MODULE = transcribe_cpp
    _BINDING_LIBRARY = library_path
    reported = getattr(transcribe_cpp, "library_path", None)
    if callable(reported):
        try:
            reported_path = Path(reported()).resolve()
        except Exception as exc:
            _BINDING_MODULE = None
            _BINDING_LIBRARY = None
            raise EngineError(
                f"could not verify the loaded native library path: {exc}"
            ) from exc
        if reported_path != library_path:
            _BINDING_MODULE = None
            _BINDING_LIBRARY = None
            raise EngineError(
                "official binding loaded an unexpected native library: "
                f"expected {library_path}, got {reported_path}"
            )
    return transcribe_cpp


def _validate_sample_rate(sample_rate) -> None:
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, int):
        raise AudioValidationError(f"sample_rate must be an integer, got {sample_rate!r}")
    if sample_rate != _SAMPLE_RATE:
        raise AudioValidationError(
            f"only {_SAMPLE_RATE} Hz mono PCM is supported; got {sample_rate} Hz"
        )


def validate_samples(samples, *, allow_empty: bool = False):
    """Copy and validate mono float PCM; return an ``array('f')``.

    Rejects strings/bytes (ambiguous encodings), non-1-D buffers, non-scalar
    entries, and NaN/+-Inf samples.  Values outside [-1, 1] are finite PCM and
    are not clamped or rejected here.
    """
    if isinstance(samples, (str, bytes, bytearray)):
        raise AudioValidationError("samples must be a sequence of float PCM values, not text/bytes")
    ndim = getattr(samples, "ndim", None)
    if ndim is not None and ndim != 1:
        raise AudioValidationError(
            f"PCM must be 1-D mono (got {ndim}-D shape {getattr(samples, 'shape', None)!r})"
        )
    try:
        count = len(samples)
    except TypeError as exc:
        raise AudioValidationError("samples must be a sized iterable of float PCM values") from exc
    if count == 0 and not allow_empty:
        raise AudioValidationError("empty audio buffer")
    if count > 2**31 - 1:
        raise AudioValidationError(f"PCM buffer is too long for the native int count: {count}")

    copied = array("f")
    for index, value in enumerate(samples):
        if isinstance(value, (str, bytes, bytearray, bool)):
            raise AudioValidationError(f"sample {index} is not a numeric PCM value")
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise AudioValidationError(f"sample {index} is not a numeric PCM value") from exc
        if not math.isfinite(number):
            raise AudioValidationError(f"sample {index} is not finite: {number!r}")
        try:
            copied.append(number)
        except OverflowError as exc:
            raise AudioValidationError(
                f"sample {index} overflows float32: {number!r}"
            ) from exc
        if not math.isfinite(copied[-1]):
            raise AudioValidationError(
                f"sample {index} overflows float32 after the required copy: {number!r}"
            )
    if len(copied) != count:
        raise AudioValidationError("sample iteration length does not match len(samples)")
    return copied


def _sanitize_decode_ms(result):
    timings = getattr(result, "timings", None)
    if timings is None:
        return None
    value = _finite_float(getattr(timings, "decode_ms", None))
    if value is None or value <= 0:
        return None
    return value


def _stream_text_view(stream):
    try:
        view = stream.text()
    except Exception as exc:
        raise EngineError(f"could not read native stream text views: {exc}") from exc
    return view


def _stream_update_fields(update) -> dict:
    if update is None:
        return {}
    return {
        "revision": _nonnegative_int(getattr(update, "revision", None)),
        "input_received_ms": _nonnegative_int(getattr(update, "input_received_ms", None)),
        "audio_committed_ms": _nonnegative_int(getattr(update, "audio_committed_ms", None)),
        "buffered_ms": _nonnegative_int(getattr(update, "buffered_ms", None)),
        "committed_changed": bool(getattr(update, "committed_changed", False)),
        "tentative_changed": bool(getattr(update, "tentative_changed", False)),
    }


def _release_stream(stream) -> None:
    """Release a native stream through the pinned binding surface.

    The official ``Stream`` has ``reset()`` (idempotent, releases the model's
    stream lease); older/alternate binding shapes may expose ``close()``.
    """
    reset = getattr(stream, "reset", None)
    if callable(reset):
        reset()
        return
    close = getattr(stream, "close", None)
    if callable(close):
        close()
        return
    raise EngineError("native stream exposes neither reset() nor close()")


class Engine:
    """A single persistent model, reusable for batch and native-stream calls."""

    def __init__(
        self,
        model_path,
        *,
        library_path=None,
        language="auto",
        threads=4,
        use_gpu=True,
    ):
        init_started = _monotonic()
        self._lock = threading.RLock()
        self._closed = False
        self._close_errors = []
        self._model = None
        self._batch_session = None
        self._stream_session = None
        self._stream = None
        self._stream_meta = None
        self._stream_active = False
        self._stream_finalized = False
        self._stream_failed = False
        self._binding = None

        if isinstance(threads, bool) or not isinstance(threads, int) or threads < 0:
            raise ValueError(f"threads must be a non-negative integer, got {threads!r}")
        if not isinstance(use_gpu, bool):
            raise ValueError(f"use_gpu must be a boolean, got {use_gpu!r}")
        if language is None:
            language = "auto"
        if not isinstance(language, str) or not language.strip():
            raise ValueError(f"language must be a non-empty string or None, got {language!r}")

        model_file = Path(model_path).expanduser()
        if not model_file.is_file():
            raise FileNotFoundError(f"model file not found: {model_file}")
        model_file = model_file.resolve()

        library_file = resolve_library_path(library_path)
        lock = _load_lock()
        artifact_record = verify_library_artifact(library_file, lock)
        binding = _load_binding(library_file)
        identity = verify_native_identity(binding, lock)

        self._threads = threads
        self._use_gpu = use_gpu
        self._default_language = language
        self._model_path = model_file
        self._library_path = library_file
        self._binding = binding
        self._lock_record = lock
        self._identity = identity
        self._artifact_record = artifact_record

        backend_policy = "auto" if use_gpu else "cpu"
        load_started = _monotonic()
        try:
            model = binding.Model(str(model_file), backend=backend_policy, no_mmap=False)
        except Exception as exc:
            raise EngineError(f"loading model {model_file.name!r} failed: {exc}") from exc
        model_load_wall_ms = (_monotonic() - load_started) * 1000.0
        self._model = model

        try:
            roles, capabilities = self._read_roles_and_capabilities()
            self._roles = roles
            self._capabilities = capabilities
            backend_evidence = self._read_backend_evidence(backend_policy)
            native_load_ms, native_load_source = self._probe_native_load_ms()
            self._default_language_info = self._resolve_language(None)
        except Exception:
            self._close_resources()
            raise

        try:
            self._info = self._build_info(
                model_file=model_file,
                library_file=library_file,
                lock=lock,
                identity=identity,
                artifact_record=artifact_record,
                roles=roles,
                capabilities=capabilities,
                backend_evidence=backend_evidence,
                native_load_ms=native_load_ms,
                native_load_source=native_load_source,
                model_load_wall_ms=model_load_wall_ms,
                constructor_wall_ms=(_monotonic() - init_started) * 1000.0,
            )
        except Exception:
            self._close_resources()
            self._closed = True
            raise

    # ------------------------------------------------------------------
    # introspection
    # ------------------------------------------------------------------
    def _read_roles_and_capabilities(self):
        caps = self._model.capabilities
        roles = []
        try:
            for role in self._model.roles:
                roles.append(getattr(role, "name", str(role)))
        except Exception:
            roles = []
        roles = sorted(set(roles))
        capabilities = {
            "batch": "ASR" in roles,
            "native_stream": bool(getattr(caps, "supports_streaming", False)),
            "timestamps": _text(getattr(caps, "max_timestamp_kind", "")) or None,
            "languages": list(getattr(caps, "languages", ()) or ()),
            "language_detect": bool(getattr(caps, "supports_language_detect", False)),
            "translate": bool(getattr(caps, "supports_translate", False)),
            "max_audio_ms": _nonnegative_int(getattr(caps, "max_audio_ms", 0)) or 0,
            "native_sample_rate": _nonnegative_int(getattr(caps, "native_sample_rate", 0)) or 0,
            "roles": roles,
        }
        capabilities["max_audio_ms_unbounded"] = capabilities["max_audio_ms"] == 0
        capabilities["languages_known"] = bool(capabilities["languages"])
        return roles, capabilities

    def _read_backend_evidence(self, requested_policy: str) -> dict:
        reported = _text(getattr(self._model, "backend", "")) or "unknown"
        device = {}
        try:
            dev = self._model.device
            device = {
                "name": _text(getattr(dev, "name", "")),
                "description": _text(getattr(dev, "description", "")),
                "kind": _text(getattr(dev, "kind", "")) or "unknown",
                "device_type": _text(getattr(dev, "device_type", "")) or "unknown",
                "device_id": _text(getattr(dev, "device_id", "")) or None,
                "memory_total_bytes": _nonnegative_int(getattr(dev, "memory_total", 0)),
                "memory_free_bytes": _nonnegative_int(getattr(dev, "memory_free", 0)),
                "index": _nonnegative_int(getattr(dev, "index", None)),
            }
            device["memory_reported"] = bool(device["memory_total_bytes"])
        except Exception as exc:
            device = {"available": False, "reason": type(exc).__name__}

        backend_available = None
        probe = getattr(self._binding, "backend_available", None)
        if callable(probe):
            try:
                backend_available = bool(probe(requested_policy))
            except Exception:
                backend_available = None
        return {
            "requested_policy": requested_policy,
            "reported_backend": reported,
            "device": device,
            "requested_backend_available_at_probe": backend_available,
            "evidence_source": "transcribe_cpp Model.backend + Model.device (native runtime)",
            "metal_build_flag_is_not_evidence": True,
        }

    def _probe_native_load_ms(self):
        """Read the model-scoped native load time without running inference.

        The high-level binding has no ASR ``Session.timings`` property, but the
        pinned low-level surface exposes ``transcribe_get_timings``.  A session
        can be created and queried before any run; ``load_ms`` is model-scoped.
        If that private surface changes, info reports null with the reason
        rather than inventing a timing.
        """
        if "ASR" not in self._roles:
            return None, "model_has_no_asr_role"
        session = None
        try:
            session = self._model.session(n_threads=self._threads)
        except Exception as exc:
            return None, f"session_unavailable:{type(exc).__name__}"
        try:
            lib = getattr(self._binding, "_lib", None)
            generated = getattr(self._binding, "_generated", None)
            if lib is None or generated is None:
                return None, "private_binding_timings_surface_unavailable"
            timings = generated.transcribe_timings()
            lib.transcribe_timings_init(ctypes.byref(timings))
            status = lib.transcribe_get_timings(getattr(session, "_h"), ctypes.byref(timings))
            if status != 0:
                return None, f"native_get_timings_status_{status}"
            value = _finite_float(getattr(timings, "load_ms", None))
            if value is None or value <= 0:
                return None, "native_load_ms_zero_or_nonfinite"
            return value, "transcribe_get_timings.load_ms"
        except Exception as exc:
            return None, f"timing_probe_error:{type(exc).__name__}"
        finally:
            try:
                session.close()
            except Exception:
                pass

    def _probe_parakeet_extension(self):
        """Probe extension-kind acceptance only; this is not a value probe."""
        options_class = getattr(self._binding, "ParakeetStreamOptions", None)
        if options_class is None:
            return None, "binding_has_no_parakeet_stream_extension"
        try:
            options = options_class(att_context_right=_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES)
            return bool(self._model.accepts(options)), "model.accepts(ParakeetStreamOptions)"
        except Exception as exc:
            return None, f"extension_probe_error:{type(exc).__name__}"

    @staticmethod
    def _new_context_record(requested_frames):
        return {
            "att_context_right_frames_requested": requested_frames,
            "att_context_right_frames_applied": None,
            "att_context_right_frames_accepted": None,
            "model_default_att_context_right_frames": None,
            "applied_context_source": "unavailable",
            "applied_context_evidence": "not applied",
            "reason": "not_started",
            "parakeet_stream_extension_accepted": None,
            "accepted_evidence": (
                "accepted (left,right) context is not exposed by the pinned native binding"
            ),
            "model_default_evidence": (
                "model default context is not exposed by the pinned native binding"
            ),
        }

    def _record_stream_context(self, context: dict) -> None:
        """Publish the last stream's context attempt/result truthfully."""
        info = getattr(self, "_info", None)
        if not isinstance(info, dict):
            return
        public = {
            "att_context_right_frames_requested": context[
                "att_context_right_frames_requested"
            ],
            "att_context_right_frames_applied": context[
                "att_context_right_frames_applied"
            ],
            "att_context_right_frames_accepted": context[
                "att_context_right_frames_accepted"
            ],
            "model_default_att_context_right_frames": context[
                "model_default_att_context_right_frames"
            ],
            "applied_context_source": context["applied_context_source"],
            "applied_context_evidence": context["applied_context_evidence"],
            "att_context_reason": context["reason"],
            "reason": context["reason"],
            "parakeet_stream_extension_accepted": context[
                "parakeet_stream_extension_accepted"
            ],
        }
        native_stream = info.setdefault("native_stream", {})
        native_stream.update(public)
        native_stream["source"] = "last_stream_attempt"
        native_stream["att_context_right_frames"] = public[
            "att_context_right_frames_accepted"
        ]
        contract = info.setdefault("stream_contract", {})
        contract.update(public)
        info.update(public)
        info["att_context_right_frames"] = public["att_context_right_frames_accepted"]
        info["default_att_context_right_frames"] = public[
            "model_default_att_context_right_frames"
        ]
        info["att_context_right_frames_model_default"] = public[
            "model_default_att_context_right_frames"
        ]

    def _build_info(self, **kwargs) -> dict:
        capabilities = kwargs["capabilities"]
        capabilities["lid"] = capabilities["language_detect"]
        capabilities["streaming"] = capabilities["native_stream"]
        model_name, model_scope = _public_path(kwargs["model_file"])
        library_name, library_scope = _public_path(kwargs["library_file"])
        binding_file = getattr(self._binding, "__file__", None)
        if binding_file:
            binding_source, binding_source_scope = _public_path(Path(binding_file).parent)
        else:
            binding_source, binding_source_scope = (
                ".tools/transcribe.cpp/bindings/python/src/transcribe_cpp",
                "project",
            )
        extension_accepted, extension_probe = self._probe_parakeet_extension()
        base_context_reason = (
            "no_stream_started"
            if capabilities["native_stream"]
            else "native_stream_unsupported"
        )
        native_stream_info = {
            "native": capabilities["native_stream"],
            "att_context_right_frames": None,
            "att_context_right_frames_requested": None,
            "att_context_right_frames_applied": None,
            "att_context_right_frames_accepted": None,
            "model_default_att_context_right_frames": None,
            "default_att_context_right_frames": None,
            "applied_context_source": "unavailable",
            "applied_context_evidence": "no stream started",
            "att_context_reason": base_context_reason,
            "reason": base_context_reason,
            "parakeet_stream_extension_accepted": extension_accepted,
            "parakeet_stream_extension_probe": extension_probe,
            "source": "not_exposed_by_engine",
            "accepted_evidence": (
                "accepted (left,right) context is not exposed by the pinned native binding"
            ),
            "model_default_evidence": (
                "model default context is not exposed by the pinned native binding"
            ),
        }
        return {
            "schema_version": 1,
            "load_ms": kwargs["native_load_ms"],
            "native_stream": native_stream_info,
            "att_context_right_frames": None,
            "att_context_right_frames_requested": None,
            "att_context_right_frames_applied": None,
            "att_context_right_frames_accepted": None,
            "model_default_att_context_right_frames": None,
            "default_att_context_right_frames": None,
            "att_context_right_frames_model_default": None,
            "applied_context_source": "unavailable",
            "applied_context_evidence": "no stream started",
            "att_context_reason": base_context_reason,
            "reason": base_context_reason,
            "resolved_language": self._default_language_info["resolved"],
            "detected_language": None,
            "lid_supported": capabilities["language_detect"],
            "engine": {
                "name": "transcribe.cpp",
                "version": kwargs["identity"]["version"],
                "native_commit": kwargs["identity"]["native_commit"],
                "pinned_revision": kwargs["identity"]["pinned_revision"],
                "library": library_name,
                "library_scope": library_scope,
                "binding": "transcribe_cpp (official stdlib-only ctypes binding)",
                "binding_version": getattr(self._binding, "__version__", None),
                "binding_source": binding_source,
                "binding_source_scope": binding_source_scope,
                "lock_verified": bool(kwargs["identity"]["verified"]),
                "artifact_sha256_verified": bool(kwargs["artifact_record"]["verified"]),
                "artifact_sha256": kwargs["artifact_record"]["sha256"],
                "artifact_size_bytes": kwargs["artifact_record"]["size_bytes"],
            },
            "model": {
                "file_name": model_name,
                "path_scope": model_scope,
                "size_bytes": kwargs["model_file"].stat().st_size,
                "arch": _text(getattr(self._model, "arch", "")) or "unknown",
                "variant": _text(getattr(self._model, "variant", "")) or "unknown",
                "roles": capabilities["roles"],
            },
            "backend": kwargs["backend_evidence"],
            "timings": {
                "native_load_ms": kwargs["native_load_ms"],
                "native_load_ms_source": kwargs["native_load_source"],
                "model_load_wall_ms": kwargs["model_load_wall_ms"],
                "constructor_wall_ms": kwargs["constructor_wall_ms"],
                "note": (
                    "constructor/model-load wall times are adapter observations; "
                    "decode_ms is null when native reports zero/unknown"
                ),
            },
            "capabilities": capabilities,
            "language": {
                "default_requested": self._default_language,
                "resolved": self._default_language_info,
                "lid_supported": capabilities["language_detect"],
                "available_languages": capabilities["languages"],
            },
            "stream_contract": {
                "feed_chunk_ms_default": _DEFAULT_FEED_CHUNK_MS,
                "feed_chunk_ms_role": "caller cadence; not a native stream field",
                "att_context_right_frames_default": _DEFAULT_ATT_CONTEXT_RIGHT_FRAMES,
                "att_context_right_frames_default_is_model_default": False,
                "att_context_right_frames_default_evidence": (
                    "Engine API default; not model-default evidence"
                ),
                "att_context_right_frames_requested": None,
                "att_context_right_frames_applied": None,
                "att_context_right_frames_accepted": None,
                "model_default_att_context_right_frames": None,
                "model_default_att_context_right_frames_evidence": (
                    "not exposed by the pinned native binding"
                ),
                "applied_context_source": "unavailable",
                "applied_context_evidence": "no stream started",
                "att_context_reason": base_context_reason,
                "commit_policy_default": _DEFAULT_COMMIT_POLICY,
                "agreement_n_default": _DEFAULT_AGREEMENT_N,
                "accepted_context_exposed_by_binding": False,
                "model_default_context_exposed_by_binding": False,
            },
            "limitations": [
                "one loaded model per engine/process; compute is serialized",
                "native streaming capability is required; no batch fallback",
                "word-end/display latency cannot be derived without gold timing",
                "decode_ms is null when the native value is zero/unknown",
                "native detected_language is empty for explicit hints or no LID",
                (
                    "the cache-aware att_context menu is model-specific and native "
                    "begin rejects values outside it (e.g. pinned Nemotron 3.5: "
                    "{0,3,6,13}, so the API default 3 is valid for that model)"
                ),
                (
                    "native committed_text and stable-prefix agreement units are "
                    "native/token-or-text units, not runner word-level LA-2 units"
                ),
                (
                    "auto language maps to the native empty/NULL hint (prompt.auto_id), "
                    "not the literal string 'auto'"
                ),
            ],
            "closed": False,
        }

    @property
    def info(self) -> dict:
        with self._lock:
            payload = copy.deepcopy(self._info)
            payload["closed"] = self._closed
            if self._close_errors:
                payload["close_errors"] = list(self._close_errors)
            return payload

    # ------------------------------------------------------------------
    # lifecycle helpers
    # ------------------------------------------------------------------
    def _ensure_open(self) -> None:
        if self._closed:
            raise EngineClosedError("engine is closed")

    def _wrap_native(self, operation: str, function):
        try:
            return function()
        except EngineError:
            raise
        except Exception as exc:
            raise EngineError(f"{operation} failed: {exc}") from exc

    def _ensure_batch_session(self):
        if self._batch_session is None:
            self._batch_session = self._wrap_native(
                "creating batch session",
                lambda: self._model.session(n_threads=self._threads),
            )
        return self._batch_session

    def _ensure_stream_session(self):
        if self._stream_session is None:
            self._stream_session = self._wrap_native(
                "creating stream session",
                lambda: self._model.session(n_threads=self._threads),
            )
        return self._stream_session

    def _close_resources(self) -> None:
        """Release stream, sessions, and model in dependency order."""
        errors = []
        stream = getattr(self, "_stream", None)
        if stream is not None:
            try:
                _release_stream(stream)
            except Exception as exc:
                errors.append(f"stream:{type(exc).__name__}")
        self._stream = None
        self._stream_active = False
        for attribute in ("_batch_session", "_stream_session"):
            session = getattr(self, attribute, None)
            if session is not None:
                try:
                    session.close()
                except Exception as exc:
                    errors.append(f"{attribute}:{type(exc).__name__}")
                setattr(self, attribute, None)
        model = getattr(self, "_model", None)
        if model is not None:
            try:
                model.close()
            except Exception as exc:
                errors.append(f"model:{type(exc).__name__}")
        self._model = None
        if errors:
            self._close_errors.extend(errors)

    def close(self) -> None:
        """Idempotently release native resources; never raises."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._close_resources()

    def __enter__(self):
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    def __del__(self):
        try:
            if not getattr(self, "_closed", True):
                self.close()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # language
    # ------------------------------------------------------------------
    def _resolve_language(self, override) -> dict:
        requested = self._default_language if override is None else override
        if requested is None:
            requested = "auto"
        if not isinstance(requested, str) or not requested.strip():
            raise ValueError(f"language must be a non-empty string, got {requested!r}")
        raw = requested.strip()
        lowered = raw.lower()
        languages = list(getattr(self, "_capabilities", {}).get("languages", ()) or ())
        lid = bool(getattr(self, "_capabilities", {}).get("language_detect", False))

        if lowered in ("auto", "autodetect"):
            return {
                "requested": raw,
                "resolved": None,
                "native_hint": None,
                "mode": "autodetect" if lid else "omitted_inapplicable",
                "mapping": None,
                "lid_supported": lid,
                "auto_sentinel": "native_null_empty_hint",
            }

        if not languages:
            return {
                "requested": raw,
                "resolved": raw,
                "native_hint": raw,
                "mode": "explicit",
                "mapping": "unvalidated_capabilities_empty",
                "lid_supported": lid,
                "auto_sentinel": None,
            }

        if raw in languages:
            resolved, mapping = raw, "exact"
        else:
            folded = {language.lower(): language for language in languages}
            if lowered in folded:
                resolved, mapping = folded[lowered], "casefold"
            else:
                primary = raw.replace("_", "-").split("-", 1)[0].lower()
                matches = [language for language in languages if language.lower() == primary]
                if matches:
                    resolved, mapping = matches[0], "primary_subtag"
                else:
                    prefix_matches = [
                        language
                        for language in languages
                        if language.replace("_", "-").split("-", 1)[0].lower() == primary
                    ]
                    if not prefix_matches:
                        raise ValueError(
                            f"language {raw!r} is not offered by the loaded model; "
                            f"available: {', '.join(languages)}"
                        )
                    resolved, mapping = prefix_matches[0], "language_prefix"

        return {
            "requested": raw,
            "resolved": resolved,
            "native_hint": resolved,
            "mode": "explicit",
            "mapping": mapping,
            "lid_supported": lid,
            "auto_sentinel": None,
        }

    def _language_payload(self, language_info: dict, result) -> dict:
        payload = dict(language_info)
        detected = _text(getattr(result, "language", "")) or None
        payload["detected"] = detected
        if detected is not None:
            payload["detected_note"] = "native_detected_language"
        elif not payload.get("lid_supported"):
            payload["detected_note"] = "model_lid_unsupported"
        elif payload.get("mode") == "explicit":
            payload["detected_note"] = "explicit_hint_suppresses_native_detection"
        else:
            payload["detected_note"] = "native_returned_empty"
        return payload

    # ------------------------------------------------------------------
    # batch
    # ------------------------------------------------------------------
    def transcribe(self, samples, *, sample_rate=16000, language=None) -> dict:
        """Transcribe one complete utterance with the persistent model."""
        with self._lock:
            self._ensure_open()
            if self._stream_active:
                raise EngineStateError(
                    "cannot run a batch call while a native stream is active; "
                    "finalize or close the stream first"
                )
            _validate_sample_rate(sample_rate)
            pcm = validate_samples(samples)
            max_audio_ms = int(self._capabilities.get("max_audio_ms") or 0)
            if max_audio_ms > 0 and len(pcm) > max_audio_ms * (_SAMPLE_RATE // 1000):
                raise AudioValidationError(
                    f"audio is {len(pcm) / _SAMPLE_RATE * 1000:.0f} ms, above the "
                    f"model limit of {max_audio_ms} ms"
                )
            language_info = self._resolve_language(language)
            session = self._ensure_batch_session()
            result = self._wrap_native(
                "batch transcribe",
                lambda: session.run(
                    pcm,
                    task="transcribe",
                    language=language_info["native_hint"],
                    timestamps="none",
                ),
            )
            return self._result_payload(
                result, final=True, language_info=language_info
            )

    def _result_payload(self, result, *, final, language_info, stream=None) -> dict:
        timestamp_kind = _text(getattr(result, "timestamp_kind", "")) or "unknown"
        times_available = timestamp_kind not in ("none", "unknown", "")
        tokens = []
        for token in getattr(result, "tokens", ()) or ():
            start = _nonnegative_int(getattr(token, "t0_ms", None)) if times_available else None
            end = _nonnegative_int(getattr(token, "t1_ms", None)) if times_available else None
            tokens.append(
                {
                    "text": _text(getattr(token, "text", "")),
                    "start_ms": start,
                    "end_ms": end,
                }
            )
        payload = {
            "text": _text(getattr(result, "text", "")),
            "tokens": tokens,
            "decode_ms": _sanitize_decode_ms(result),
            "final": bool(final),
            "timestamp_kind": timestamp_kind,
            "language": self._language_payload(language_info, result),
        }
        language_payload = payload["language"]
        payload["requested_language"] = language_payload["requested"]
        payload["resolved_language"] = language_payload["resolved"]
        payload["detected_language"] = language_payload["detected"]
        payload["lid_supported"] = language_payload["lid_supported"]
        if stream is not None:
            context = dict((self._stream_meta or {}).get("att_context") or {})
            payload["native_stream"] = context
            payload["att_context_right_frames_requested"] = context.get(
                "att_context_right_frames_requested"
            )
            payload["att_context_right_frames_applied"] = context.get(
                "att_context_right_frames_applied"
            )
            payload["att_context_right_frames_accepted"] = context.get(
                "att_context_right_frames_accepted"
            )
            payload["att_context_right_frames_model_default"] = context.get(
                "model_default_att_context_right_frames"
            )
            payload["model_default_att_context_right_frames"] = context.get(
                "model_default_att_context_right_frames"
            )
            payload["applied_context_source"] = context.get(
                "applied_context_source", "unavailable"
            )
            payload["applied_context_evidence"] = context.get(
                "applied_context_evidence"
            )
            payload["att_context_reason"] = context.get("reason")
            payload["feed_chunk_ms"] = (self._stream_meta or {}).get("feed_chunk_ms")
            payload["commit_policy_native"] = (self._stream_meta or {}).get(
                "commit_policy_native"
            )
            payload["agreement_n"] = (self._stream_meta or {}).get("agreement_n")
            view = _stream_text_view(stream)
            payload["committed_text"] = _text(getattr(view, "committed", ""))
            payload["tentative_text"] = _text(getattr(view, "tentative", ""))
            payload["display_text"] = _text(
                getattr(view, "display", None)
                if getattr(view, "display", None) is not None
                else _text(getattr(view, "committed", "")) + _text(getattr(view, "tentative", ""))
            )
            if final:
                payload["final_text"] = _text(getattr(result, "text", ""))
        return payload

    # ------------------------------------------------------------------
    # native streaming
    # ------------------------------------------------------------------
    def start_stream(
        self,
        *,
        feed_chunk_ms=_DEFAULT_FEED_CHUNK_MS,
        att_context_right_frames=_DEFAULT_ATT_CONTEXT_RIGHT_FRAMES,
        language=None,
        commit_policy=_DEFAULT_COMMIT_POLICY,
        agreement_n=_DEFAULT_AGREEMENT_N,
    ) -> None:
        """Start a genuine native stream; never silently fall back to batch."""
        with self._lock:
            self._ensure_open()
            if self._stream_active:
                raise EngineStateError(
                    "a native stream is already active; finalize or close it first"
                )
            if not self._capabilities.get("native_stream"):
                raise UnsupportedCapability(
                    "the loaded model does not advertise native streaming; "
                    "batch decoding is not substituted for streaming"
                )
            if not self._capabilities.get("batch"):
                raise UnsupportedCapability("the loaded model has no ASR role")

            chunk_ms = _finite_float(feed_chunk_ms)
            if chunk_ms is None or chunk_ms <= 0:
                raise ValueError(
                    f"feed_chunk_ms must be a positive finite number, got {feed_chunk_ms!r}"
                )
            if isinstance(att_context_right_frames, bool) or not isinstance(
                att_context_right_frames, int
            ):
                raise ValueError(
                    "att_context_right_frames must be an integer (-1 for model "
                    f"default), got {att_context_right_frames!r}"
                )
            if att_context_right_frames < -1:
                raise ValueError(
                    "att_context_right_frames must be -1 or non-negative, got "
                    f"{att_context_right_frames}"
                )
            if isinstance(agreement_n, bool) or not isinstance(agreement_n, int) or agreement_n < 1:
                raise ValueError(f"agreement_n must be a positive integer, got {agreement_n!r}")
            if not isinstance(commit_policy, str):
                raise ValueError(f"commit_policy must be a string, got {commit_policy!r}")
            native_policy = _SUPPORTED_COMMIT_POLICIES.get(commit_policy.strip().lower())
            if native_policy is None:
                raise ValueError(
                    f"unsupported commit policy {commit_policy!r}; expected one of "
                    "stable-prefix, auto, on-finalize"
                )

            language_info = self._resolve_language(language)

            context_record = self._new_context_record(att_context_right_frames)
            options_class = getattr(self._binding, "ParakeetStreamOptions", None)
            if options_class is None:
                context_record["reason"] = "binding_has_no_parakeet_stream_extension"
                context_record["applied_context_evidence"] = (
                    "binding lacks the Parakeet stream extension; requested context not applied"
                )
                self._record_stream_context(context_record)
                raise UnsupportedCapability(
                    "the pinned binding has no Parakeet cache-aware stream "
                    f"extension, so requested att_context_right_frames="
                    f"{att_context_right_frames} cannot be applied; refusing to "
                    "run with an unlabelled model/family default"
                )
            try:
                options = options_class(att_context_right=att_context_right_frames)
            except Exception as exc:
                context_record["reason"] = "extension_option_construction_failed"
                self._record_stream_context(context_record)
                raise EngineError(
                    "could not construct Parakeet stream options for requested "
                    f"att_context_right_frames={att_context_right_frames}: {exc}"
                ) from exc
            try:
                extension_accepted = bool(self._model.accepts(options))
            except Exception as exc:
                context_record["reason"] = (
                    f"extension_probe_error:{type(exc).__name__}"
                )
                self._record_stream_context(context_record)
                raise EngineError(
                    "could not probe whether the model accepts the Parakeet "
                    f"cache-aware stream extension: {exc}"
                ) from exc
            context_record["parakeet_stream_extension_accepted"] = extension_accepted
            if not extension_accepted:
                context_record["reason"] = (
                    "model_does_not_accept_parakeet_stream_extension"
                )
                context_record["applied_context_evidence"] = (
                    "model.accepts(ParakeetStreamOptions) was false; requested context not applied"
                )
                self._record_stream_context(context_record)
                raise UnsupportedCapability(
                    "the loaded model does not accept the Parakeet cache-aware "
                    "stream extension, so requested att_context_right_frames="
                    f"{att_context_right_frames} cannot be applied; refusing to "
                    "fall back silently to the model/family default"
                )

            self._discard_finished_stream()
            session = self._ensure_stream_session()
            stream_kwargs = {
                "task": "transcribe",
                "language": language_info["native_hint"],
                "timestamps": "none",
                "commit_policy": native_policy,
                "stable_prefix_agreement_n": agreement_n,
                "family": options,
            }

            try:
                stream = session.stream(**stream_kwargs)
            except Exception as exc:
                context_record["reason"] = "native_begin_rejected"
                context_record["att_context_right_frames_applied"] = None
                context_record["applied_context_source"] = "unavailable"
                context_record["applied_context_evidence"] = (
                    "native transcribe_stream_begin rejected the requested context"
                )
                self._record_stream_context(context_record)
                raise EngineError(
                    "native transcribe_stream_begin failed for "
                    f"att_context_right_frames={att_context_right_frames} "
                    f"(feed_chunk_ms={chunk_ms:g}, commit_policy={native_policy}, "
                    f"agreement_n={agreement_n}): {exc}. The cache-aware context "
                    "menu is model-specific; the pinned Nemotron 3.5 model "
                    "documents {0,3,6,13} frames. Pass an accepted value explicitly."
                ) from exc

            if att_context_right_frames >= 0:
                context_record["att_context_right_frames_applied"] = (
                    att_context_right_frames
                )
                context_record["applied_context_source"] = "native"
                context_record["applied_context_evidence"] = (
                    "native transcribe_stream_begin succeeded with the requested "
                    "cache-aware value; accepted (left,right) not exposed"
                )
                context_record["reason"] = "applied_native_begin_accepted"
            else:
                # -1 asks for the model default; the numeric default is not
                # exposed, so applied stays null rather than guessed.
                context_record["att_context_right_frames_applied"] = None
                context_record["applied_context_source"] = "unavailable"
                context_record["applied_context_evidence"] = (
                    "model default requested; numeric default not exposed"
                )
                context_record["reason"] = "model_default_requested_not_exposed"
            self._stream = stream
            self._stream_active = True
            self._stream_finalized = False
            self._stream_failed = False
            self._stream_meta = {
                "feed_chunk_ms": chunk_ms,
                "feed_chunk_role": "caller cadence; not a native stream field",
                "att_context": context_record,
                "commit_policy_requested": commit_policy,
                "commit_policy_native": native_policy,
                "agreement_n": agreement_n,
                "language": language_info,
            }
            self._record_stream_context(context_record)

    def _discard_finished_stream(self) -> None:
        stream = self._stream
        if stream is None:
            return
        try:
            _release_stream(stream)
        except Exception as exc:
            self._close_errors.append(f"previous_stream:{type(exc).__name__}")
        finally:
            self._stream = None
            self._stream_active = False
            self._stream_finalized = False
            self._stream_failed = False
            self._stream_meta = None

    def feed(self, samples, *, final=False) -> dict:
        """Feed PCM to the active native stream, optionally finalizing.

        ``final=False`` requires non-empty audio.  ``final=True`` with audio
        feeds then finalizes; ``final=True`` with no audio flushes only.
        """
        with self._lock:
            self._ensure_open()
            if self._stream_failed:
                raise EngineStateError("native stream failed; start a new stream")
            if self._stream_finalized:
                raise EngineStateError("native stream already finalized; start a new stream")
            if not self._stream_active or self._stream is None:
                raise EngineStateError("no active native stream; call start_stream() first")

            pcm = validate_samples(samples, allow_empty=True)
            stream = self._stream
            if not final:
                if len(pcm) == 0:
                    raise AudioValidationError("empty non-final feed is not allowed")
                stage = "feed"
                try:
                    update = stream.feed(pcm)
                    stage = "snapshot"
                    result = stream.snapshot()
                    stage = "text_views"
                    payload = self._result_payload(
                        result,
                        final=False,
                        language_info=self._stream_meta["language"],
                        stream=stream,
                    )
                except Exception as exc:
                    state = self._mark_stream_failure(stream)
                    raise EngineError(
                        f"native stream {stage} failed (state={state}): {exc}"
                    ) from exc
                payload.update(_stream_update_fields(update))
                payload["stream_state"] = self._stream_state(stream)
                return payload

            stage = "feed" if len(pcm) > 0 else "finalize"
            feed_update = None
            try:
                if len(pcm) > 0:
                    feed_update = stream.feed(pcm)
                    stage = "finalize"
                final_update = stream.finalize()
                stage = "snapshot"
                result = stream.snapshot()
            except Exception as exc:
                state = self._mark_stream_failure(stream)
                raise EngineError(
                    f"native stream {stage} failed (state={state}): {exc}"
                ) from exc
            self._stream_active = False
            self._stream_finalized = True
            payload = self._result_payload(
                result,
                final=True,
                language_info=self._stream_meta["language"],
                stream=stream,
            )
            payload.update(_stream_update_fields(final_update))
            if feed_update is not None:
                payload["committed_changed"] = bool(
                    payload.get("committed_changed")
                    or getattr(feed_update, "committed_changed", False)
                )
                payload["tentative_changed"] = bool(
                    payload.get("tentative_changed")
                    or getattr(feed_update, "tentative_changed", False)
                )
            payload["stream_state"] = self._stream_state(stream)
            return payload

    def _mark_stream_failure(self, stream) -> str:
        """Synchronize adapter lifecycle with the native stream after an error.

        The official binding releases the stream lease when a native feed call
        leaves the stream FAILED (or FINISHED).  A pre-native error such as
        Busy keeps the stream ACTIVE.  Only terminal states change adapter
        flags, so a retryable pre-native error does not strand the adapter.
        """
        state = self._stream_state(stream)
        try:
            last_status = getattr(stream, "last_status", None)
        except Exception:
            last_status = None
        if state in ("active", "unknown", ""):
            if last_status is not None:
                self._stream_active = False
                self._stream_failed = True
            return state
        self._stream_active = False
        if state == "finished":
            self._stream_finalized = True
        else:
            self._stream_failed = True
        return state

    @staticmethod
    def _stream_state(stream) -> str:
        try:
            return _text(getattr(stream, "state", "")) or "unknown"
        except Exception:
            return "unknown"


def _monotonic() -> float:
    # Imported lazily so tests can patch a fake clock without touching time.
    import time

    return time.perf_counter()
