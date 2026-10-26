"""Unit tests for the pinned persistent engine adapter (no real inference).

The tests use an in-process fake of the official high-level binding surface.
They never load a model, never import the native library, and never run timed
inference.  One temporary git repository exercises the source-pin tamper guard
from ``tools/build_engine.py``.
"""

from __future__ import annotations

import ctypes
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from array import array
from pathlib import Path
from unittest import mock

SPIKE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPIKE_ROOT))

import backend

TOOLS_DIR = SPIKE_ROOT / "tools"


# ---------------------------------------------------------------------------
# fake official binding
# ---------------------------------------------------------------------------
class FakeRole:
    def __init__(self, name):
        self.name = name


class FakeDevice:
    name = "MTL0"
    description = "fake metal device"
    kind = "metal"
    device_type = "gpu"
    device_id = None
    memory_total = 26_800_000_000
    memory_free = 20_000_000_000
    index = 0


class FakeCapabilities:
    native_sample_rate = 16000
    max_timestamp_kind = "token"
    supports_translate = False
    translate_target_languages = ()

    def __init__(self):
        self.languages = ("en", "es")
        self.supports_language_detect = False
        self.supports_streaming = True
        self.supports_spec_decode = False
        self.max_audio_ms = 0


class ResultTimings:
    def __init__(self, load_ms=0.0, decode_ms=0.0):
        self.load_ms = load_ms
        self.decode_ms = decode_ms


class FakeTimingsStruct(ctypes.Structure):
    _fields_ = [
        ("struct_size", ctypes.c_uint64),
        ("load_ms", ctypes.c_float),
        ("mel_ms", ctypes.c_float),
        ("encode_ms", ctypes.c_float),
        ("decode_ms", ctypes.c_float),
    ]


class FakeToken:
    def __init__(self, text, t0_ms=0, t1_ms=0):
        self.text = text
        self.t0_ms = t0_ms
        self.t1_ms = t1_ms


class FakeResult:
    def __init__(self, text, *, timestamp_kind="none", language="", decode_ms=0.0, tokens=None):
        self.text = text
        self.raw_text = text
        self.language = language
        self.timestamp_kind = timestamp_kind
        self.segments = ()
        self.speaker_segments = ()
        self.words = ()
        self.tokens = tuple(tokens or ())
        self.timings = ResultTimings(decode_ms=decode_ms)


class FakeStreamText:
    def __init__(self, full, committed, tentative):
        self.full = full
        self.committed = committed
        self.tentative = tentative

    @property
    def display(self):
        return self.committed + self.tentative


class FakeUpdate:
    def __init__(self, *, revision, final=False, input_received_ms=1120, buffered_ms=0):
        self.result_changed = True
        self.is_final = final
        self.revision = revision
        self.input_received_ms = input_received_ms
        self.audio_committed_ms = input_received_ms
        self.buffered_ms = buffered_ms
        self.committed_changed = True
        self.tentative_changed = True


class FakeStream:
    def __init__(self, session, owner, kwargs):
        self.session = session
        self.owner = owner
        self.kwargs = kwargs
        self.state = "active"
        self.revision = 0
        self.feed_calls = []
        self.finalize_calls = 0
        self.reset_calls = 0

    def feed(self, pcm):
        self.owner.feed_calls += 1
        self.feed_calls.append(list(pcm))
        if self.owner.fail_feed:
            self.state = "failed"
            raise RuntimeError("fake native feed failed")
        self.revision += 1
        return FakeUpdate(revision=self.revision, input_received_ms=len(pcm) // 16)

    def finalize(self):
        if self.owner.fail_finalize:
            self.state = "failed"
            raise RuntimeError("fake native finalize failed")
        self.finalize_calls += 1
        self.state = "finished"
        self.revision += 1
        return FakeUpdate(revision=self.revision, final=True, input_received_ms=2240)

    def snapshot(self):
        if self.owner.fail_snapshot:
            if self.owner.fail_snapshot in ("failed", "finished", "idle"):
                self.state = self.owner.fail_snapshot
            raise RuntimeError("fake native snapshot failed")
        finished = self.state == "finished"
        text = self.owner.final_text if finished else self.owner.partial_text
        return FakeResult(
            text,
            timestamp_kind=self.owner.timestamp_kind,
            language=self.owner.detected_language,
            decode_ms=self.owner.decode_ms,
            tokens=[
                FakeToken("hola", 0, 400),
                FakeToken("mundo", 400, 900),
            ],
        )

    def text(self):
        if self.owner.fail_text_view:
            if self.owner.fail_text_view in ("failed", "finished", "idle"):
                self.state = self.owner.fail_text_view
            raise RuntimeError("fake native text view failed")
        if self.state == "finished":
            return FakeStreamText(self.owner.final_text, self.owner.committed_text, "")
        return FakeStreamText(
            self.owner.partial_text, self.owner.committed_text, self.owner.partial_text
        )

    def reset(self):
        self.reset_calls += 1
        self.state = "idle"


class FakeSession:
    def __init__(self, model):
        self.model = model
        self.owner = model.owner
        self.run_calls = []
        self.stream_calls = []
        self.closed = False
        self._h = 1234

    def run(self, pcm, *, task, language, timestamps):
        self.owner.run_calls += 1
        self.run_calls.append(
            {
                "pcm": list(pcm),
                "task": task,
                "language": language,
                "timestamps": timestamps,
            }
        )
        return FakeResult(
            self.owner.batch_text,
            timestamp_kind=self.owner.timestamp_kind,
            language="" if language else self.owner.detected_language,
            decode_ms=self.owner.decode_ms,
            tokens=[FakeToken("hola", 0, 400), FakeToken("mundo", 400, 900)],
        )

    def stream(self, **kwargs):
        self.owner.stream_begin_calls += 1
        self.stream_calls.append(kwargs)
        if self.owner.reject_stream_begin:
            raise RuntimeError("fake native begin rejected the requested context")
        stream = FakeStream(self, self.owner, kwargs)
        self.owner.streams.append(stream)
        return stream

    def close(self):
        self.closed = True


class FakeModel:
    def __init__(self, path, *, backend, no_mmap):
        self.owner = self._owner
        self.path = path
        self.backend = (
            self.owner.model_backend
            if self.owner.model_backend is not None
            else backend
        )
        self.no_mmap = no_mmap
        self._arch = "parakeet"
        self.variant = "tdt-0.6b-v3"
        self.capabilities = self.owner.capabilities
        self.roles = [FakeRole("ASR")]
        self.closed = False
        self.owner.model_loads += 1
        self.owner.models.append(self)

    @property
    def arch(self):
        if self.owner.arch_raises:
            raise RuntimeError("fake arch query failed")
        return self._arch

    @property
    def device(self):
        if self.owner.device_raises:
            raise RuntimeError("fake device query failed")
        return FakeDevice()

    def session(self, *, n_threads=0, kv_type="auto", n_ctx=0):
        session = FakeSession(self)
        self.owner.sessions.append(session)
        return session

    def accepts(self, options):
        return self.owner.accepts_parakeet_stream

    def close(self):
        self.closed = True
        self.owner.model_closed = True


class FakeLib:
    def __init__(self, owner):
        self.owner = owner

    def transcribe_timings_init(self, out):
        pass

    def transcribe_get_timings(self, handle, out):
        target = getattr(out, "_obj", None)
        if target is not None:
            target.load_ms = self.owner.native_load_ms
        return 0


class FakeGenerated:
    @staticmethod
    def transcribe_timings():
        return FakeTimingsStruct()


class ParakeetStreamOptions:
    def __init__(self, *, att_context_right=None):
        self.att_context_right = att_context_right


class FakeOwner:
    def __init__(self):
        self.model_loads = 0
        self.run_calls = 0
        self.stream_begin_calls = 0
        self.feed_calls = 0
        self.models = []
        self.sessions = []
        self.streams = []
        self.model_closed = False
        self.capabilities = FakeCapabilities()
        self.model_backend = None
        self.device_raises = False
        self.arch_raises = False
        self.accepts_parakeet_stream = True
        self.reject_stream_begin = False
        self.fail_feed = False
        self.fail_finalize = False
        self.fail_snapshot = None
        self.fail_text_view = None
        self.native_load_ms = 12.5
        self.batch_text = "hola mundo"
        self.partial_text = "hola"
        self.final_text = "hola mundo"
        self.committed_text = "hola"
        self.detected_language = ""
        self.timestamp_kind = "none"
        self.decode_ms = 0.0

    def binding(self, *, private_timings=True):
        owner = self

        class BoundModel(FakeModel):
            _owner = owner

        namespace = types.SimpleNamespace(
            Model=BoundModel,
            Session=FakeSession,
            Stream=FakeStream,
            ParakeetStreamOptions=ParakeetStreamOptions,
            __version__="0.4.1",
            native_version=lambda: "0.4.1",
            native_commit=lambda: "8facde6",
            backend_available=lambda policy: True,
        )
        if private_timings:
            namespace._lib = FakeLib(owner)
            namespace._generated = FakeGenerated()
        return namespace


def fake_lock(**overrides):
    lock = {
        "schema_version": 1,
        "engine": {
            "repository": "https://github.com/handy-computer/transcribe.cpp",
            "revision": "8facde6fcd8fb9caa585a5788ab450df6e8ec7db",
            "version": "0.4.1",
        },
        "artifact": {
            "path": ".tools/build/src/libtranscribe.dylib",
            "sha256": "0" * 64,
            "size_bytes": 1,
        },
    }
    lock.update(overrides)
    return lock


def write_fake_binding_package(
    src: Path, *, raises: bool = False, reported_library: str | None = None
) -> Path:
    package = src / "transcribe_cpp"
    package.mkdir(parents=True, exist_ok=True)
    library_line = (
        f"_LIB = {reported_library!r}"
        if reported_library is not None
        else '_LIB = os.environ.get("TRANSCRIBE_LIBRARY")'
    )
    body = """
import json
import os
import sys
from pathlib import Path

__version__ = "0.4.1"
%s

def library_path():
    return _LIB

record = os.environ.get("FAKE_BINDING_RECORD")
if record:
    Path(record).write_text(json.dumps({
        "env": os.environ.get("TRANSCRIBE_LIBRARY"),
        "path0": sys.path[0] if sys.path else None,
        "package": str(Path(__file__).resolve()),
    }))
if %r:
    raise RuntimeError("fake binding import failure")
""" % (library_line, raises)
    (package / "__init__.py").write_text(body, encoding="utf-8")
    return package


def drop_transcribe_modules():
    for name in [
        n for n in sys.modules if n == "transcribe_cpp" or n.startswith("transcribe_cpp.")
    ]:
        sys.modules.pop(name, None)


class EngineTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmpdir = Path(self.tmp.name)
        self.model_path = self.tmpdir / "fake-model.gguf"
        self.model_path.write_bytes(b"GGUF-fake-model")
        self.library_path = self.tmpdir / "libtranscribe.dylib"
        self.library_path.write_bytes(b"fake-native-library")
        self.owner = FakeOwner()
        self.binding = self.owner.binding()
        self.lock = fake_lock()
        self._real_load_lock = backend._load_lock
        self._real_load_binding = backend._load_binding
        self.patches = [
            mock.patch.object(backend, "_load_lock", return_value=self.lock),
            mock.patch.object(backend, "_load_binding", return_value=self.binding),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.engine = None

    def make_engine(self, **kwargs):
        self.engine = backend.Engine(
            str(self.model_path),
            library_path=str(self.library_path),
            **kwargs,
        )
        self.addCleanup(self.engine.close)
        return self.engine

    # ------------------------------------------------------------------
    # info / persistence
    # ------------------------------------------------------------------
    def test_info_is_serializable_and_reports_native_evidence(self):
        engine = self.make_engine()
        info = engine.info
        json.dumps(info, allow_nan=False)
        self.assertEqual(info["engine"]["name"], "transcribe.cpp")
        self.assertEqual(info["engine"]["pinned_revision"], self.lock["engine"]["revision"])
        self.assertTrue(info["engine"]["lock_verified"])
        self.assertFalse(info["engine"]["artifact_sha256_verified"])
        self.assertEqual(info["model"]["file_name"], "fake-model.gguf")
        self.assertEqual(info["model"]["path_scope"], "external")
        self.assertEqual(info["backend"]["reported_backend"], "auto")
        self.assertEqual(info["backend"]["device"]["kind"], "metal")
        self.assertTrue(info["capabilities"]["native_stream"])
        self.assertEqual(info["timings"]["native_load_ms"], 12.5)
        self.assertEqual(info["load_ms"], 12.5)
        self.assertTrue(info["native_stream"]["native"])
        self.assertIsNone(info["native_stream"]["att_context_right_frames"])
        self.assertTrue(
            info["native_stream"]["parakeet_stream_extension_accepted"]
        )
        self.assertIsNone(
            info["stream_contract"]["att_context_right_frames_requested"]
        )
        self.assertFalse(
            info["stream_contract"]["att_context_right_frames_default_is_model_default"]
        )
        self.assertEqual(info["capabilities"]["lid"], False)
        self.assertEqual(info["capabilities"]["streaming"], True)
        self.assertIsInstance(info["timings"]["constructor_wall_ms"], float)
        self.assertGreaterEqual(info["timings"]["constructor_wall_ms"], 0.0)
        self.assertEqual(info["stream_contract"]["feed_chunk_ms_role"],
                         "caller cadence; not a native stream field")
        self.assertFalse(info["closed"])
        self.assertEqual(self.owner.model_loads, 1)

        info["model"]["file_name"] = "mutated"
        self.assertEqual(engine.info["model"]["file_name"], "fake-model.gguf")

    def test_native_load_probe_absent_reports_null_and_reason(self):
        binding = self.owner.binding(private_timings=False)
        with mock.patch.object(backend, "_load_binding", return_value=binding):
            engine = self.make_engine()
        info = engine.info
        self.assertIsNone(info["timings"]["native_load_ms"])
        self.assertEqual(
            info["timings"]["native_load_ms_source"],
            "private_binding_timings_surface_unavailable",
        )

    def test_nonfinite_native_load_is_null_and_strict_json(self):
        self.owner.native_load_ms = float("nan")
        engine = self.make_engine()
        info = engine.info
        self.assertIsNone(info["timings"]["native_load_ms"])
        self.assertIsNone(info["load_ms"])
        self.assertEqual(
            info["timings"]["native_load_ms_source"],
            "native_load_ms_zero_or_nonfinite",
        )
        json.dumps(info, allow_nan=False)

    def test_build_info_failure_closes_model_before_propagating(self):
        self.owner.arch_raises = True
        with self.assertRaises(RuntimeError) as caught:
            backend.Engine(
                str(self.model_path),
                library_path=str(self.library_path),
            )
        # Keep the exception/traceback alive while checking: without explicit
        # constructor cleanup, __del__ may otherwise hide the leak.
        self.assertIsNotNone(caught.exception)
        self.assertTrue(self.owner.model_closed)

    def test_batch_reuses_one_model_and_one_batch_session(self):
        engine = self.make_engine(threads=2)
        first = engine.transcribe([0.0] * 160, language="en")
        engine.transcribe([0.0] * 160, language="es")
        third = engine.transcribe([0.0] * 160, language="auto")
        self.assertEqual(first["text"], "hola mundo")
        self.assertTrue(first["final"])
        self.assertNotIn("committed_text", first)
        self.assertEqual(self.owner.model_loads, 1)
        self.assertEqual(self.owner.run_calls, 3)
        # probe session + one reused batch session
        self.assertEqual(len(self.owner.sessions), 2)
        self.assertEqual(self.owner.sessions[-1].run_calls[0]["pcm"][0], 0.0)
        self.assertEqual([call["language"] for call in self.owner.sessions[-1].run_calls],
                         ["en", "es", None])
        self.assertEqual(first["language"]["mapping"], "exact")
        self.assertEqual(first["language"]["mode"], "explicit")
        self.assertEqual(first["language"]["detected_note"], "model_lid_unsupported")
        self.assertEqual(first["requested_language"], "en")
        self.assertEqual(first["resolved_language"], "en")
        self.assertIsNone(first["detected_language"])
        self.assertIs(first["lid_supported"], False)
        self.assertEqual(third["language"]["mode"], "omitted_inapplicable")
        self.assertEqual(third["language"]["detected_note"], "model_lid_unsupported")

    def test_region_language_maps_to_primary_subtag_without_reload(self):
        engine = self.make_engine()
        result = engine.transcribe([0.0] * 160, language="es-US")
        self.assertEqual(result["language"]["requested"], "es-US")
        self.assertEqual(result["language"]["resolved"], "es")
        self.assertEqual(result["language"]["mapping"], "primary_subtag")
        self.assertEqual(self.owner.sessions[-1].run_calls[0]["language"], "es")
        self.assertEqual(self.owner.model_loads, 1)

    def test_casefold_language_mapping(self):
        engine = self.make_engine()
        result = engine.transcribe([0.0] * 160, language="ES")
        self.assertEqual(result["language"]["resolved"], "es")
        self.assertEqual(result["language"]["mapping"], "casefold")

    def test_nemotron_locale_exact_and_auto_sentinel(self):
        self.owner.capabilities.languages = ("en-US", "es-US", "es-ES")
        self.owner.capabilities.supports_language_detect = True
        self.owner.detected_language = "es-US"
        engine = self.make_engine()
        auto = engine.transcribe([0.0] * 160, language="auto")
        self.assertIsNone(auto["language"]["native_hint"])
        self.assertEqual(auto["language"]["auto_sentinel"], "native_null_empty_hint")
        self.assertEqual(self.owner.sessions[-1].run_calls[-1]["language"], None)
        self.assertEqual(auto["language"]["detected"], "es-US")
        self.assertEqual(auto["language"]["detected_note"], "native_detected_language")
        exact = engine.transcribe([0.0] * 160, language="es-US")
        self.assertEqual(exact["language"]["resolved"], "es-US")
        self.assertEqual(exact["language"]["mapping"], "exact")
        self.assertEqual(self.owner.sessions[-1].run_calls[-1]["language"], "es-US")
        self.assertIsNone(exact["language"]["detected"])
        self.assertEqual(
            exact["language"]["detected_note"],
            "explicit_hint_suppresses_native_detection",
        )
        self.assertEqual(self.owner.model_loads, 1)

    def test_locale_without_exact_region_uses_declared_language_prefix(self):
        self.owner.capabilities.languages = ("en-US", "es-US", "es-ES")
        engine = self.make_engine()
        result = engine.transcribe([0.0] * 160, language="es-419")
        self.assertEqual(result["language"]["resolved"], "es-US")
        self.assertEqual(result["language"]["mapping"], "language_prefix")
        self.assertEqual(self.owner.sessions[-1].run_calls[-1]["language"], "es-US")
        self.assertEqual(self.owner.model_loads, 1)

    def test_unsupported_language_rejected_before_native_call(self):
        engine = self.make_engine()
        with self.assertRaises(ValueError):
            engine.transcribe([0.0] * 160, language="fr")
        self.assertEqual(self.owner.run_calls, 0)

    def test_invalid_constructor_language_rejected(self):
        with self.assertRaises(ValueError):
            self.make_engine(language="   ")
        with self.assertRaises(ValueError):
            self.make_engine(language=5)
        with self.assertRaises(ValueError):
            self.make_engine(threads=True)
        with self.assertRaises(ValueError):
            self.make_engine(use_gpu="yes")

    # ------------------------------------------------------------------
    # audio validation
    # ------------------------------------------------------------------
    def test_invalid_samples_and_rates_rejected(self):
        engine = self.make_engine()
        bad_samples = [
            [float("nan")],
            [float("inf")],
            [float("-inf")],
            [0.0, "0.5"],
            [0.0, None],
            [[0.0], [0.1]],
            b"\x00\x00",
            [],
        ]
        for samples in bad_samples:
            with self.subTest(samples=samples), self.assertRaises(ValueError):
                engine.transcribe(samples)
        for rate in (8000, 44100, 0, 16000.0, True):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                engine.transcribe([0.0], sample_rate=rate)
        self.assertEqual(self.owner.run_calls, 0)

    def test_model_audio_limit_rejected_before_native_call(self):
        engine = self.make_engine()
        engine._capabilities["max_audio_ms"] = 100
        with self.assertRaises(ValueError):
            engine.transcribe([0.0] * 1601)
        self.assertEqual(self.owner.run_calls, 0)

    def test_float64_values_that_overflow_float32_are_rejected(self):
        engine = self.make_engine()
        for value in (1e300, -1e300, 3.5e38, -3.5e38):
            with self.subTest(value=value), self.assertRaises(
                backend.AudioValidationError
            ):
                engine.transcribe([0.0, value, 0.0])
        self.assertEqual(self.owner.run_calls, 0)

    def test_array_f_pcm_and_no_clamping(self):
        engine = self.make_engine()
        samples = array("f", [0.5, -2.0, 0.0])
        engine.transcribe(samples)
        recorded = self.owner.sessions[-1].run_calls[0]["pcm"]
        self.assertEqual(recorded, [0.5, -2.0, 0.0])

    def test_token_times_null_when_timestamp_kind_none(self):
        engine = self.make_engine()
        result = engine.transcribe([0.0] * 160)
        self.assertEqual(result["timestamp_kind"], "none")
        self.assertTrue(result["tokens"])
        self.assertTrue(all(tok["start_ms"] is None and tok["end_ms"] is None
                            for tok in result["tokens"]))

    def test_token_times_preserved_when_available(self):
        self.owner.timestamp_kind = "token"
        engine = self.make_engine()
        result = engine.transcribe([0.0] * 160)
        self.assertEqual(result["tokens"][0]["start_ms"], 0)
        self.assertEqual(result["tokens"][0]["end_ms"], 400)

    def test_decode_ms_zero_or_nonfinite_is_null(self):
        engine = self.make_engine()
        result = engine.transcribe([0.0] * 160)
        self.assertIsNone(result["decode_ms"])
        self.owner.decode_ms = 7.25
        self.assertEqual(engine.transcribe([0.0] * 160)["decode_ms"], 7.25)
        self.owner.decode_ms = float("nan")
        self.assertIsNone(engine.transcribe([0.0] * 160)["decode_ms"])
        json.dumps(engine.info, allow_nan=False)

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------
    def test_stream_lifecycle_errors_and_empty_final_flush(self):
        engine = self.make_engine()
        with self.assertRaises(backend.EngineStateError):
            engine.feed([0.0])
        engine.start_stream()
        with self.assertRaises(backend.EngineStateError):
            engine.start_stream()
        with self.assertRaises(ValueError):
            engine.feed([])
        flushed = engine.feed([], final=True)
        self.assertTrue(flushed["final"])
        self.assertEqual(flushed["final_text"], "hola mundo")
        self.assertEqual(flushed["committed_text"], "hola")
        # The pinned native contract: finalize empties tentative; committed may
        # remain the shorter stable prefix, while final_text is authoritative.
        self.assertEqual(flushed["display_text"], "hola")
        self.assertEqual(self.owner.streams[0].feed_calls, [])
        with self.assertRaises(backend.EngineStateError):
            engine.feed([0.0])

    def test_nonempty_final_feeds_then_finalizes(self):
        engine = self.make_engine()
        engine.start_stream(feed_chunk_ms=1120)
        result = engine.feed([0.1] * 32, final=True)
        stream = self.owner.streams[0]
        self.assertEqual(len(stream.feed_calls), 1)
        self.assertEqual(len(stream.feed_calls[0]), 32)
        for value in stream.feed_calls[0]:
            self.assertAlmostEqual(value, 0.1, places=6)
        self.assertEqual(stream.finalize_calls, 1)
        self.assertTrue(result["final"])
        self.assertEqual(result["final_text"], "hola mundo")
        self.assertEqual(result["text"], "hola mundo")
        self.assertEqual(result["stream_state"], "finished")

    def test_nonfinal_feed_exposes_stream_fields(self):
        engine = self.make_engine()
        engine.start_stream()
        result = engine.feed([0.25] * 16)
        self.assertFalse(result["final"])
        self.assertEqual(result["text"], "hola")
        self.assertEqual(result["committed_text"], "hola")
        self.assertEqual(result["tentative_text"], "hola")
        self.assertEqual(result["display_text"], "holahola")
        self.assertNotIn("final_text", result)
        self.assertEqual(result["revision"], 1)
        self.assertEqual(result["input_received_ms"], 1)
        self.assertEqual(result["buffered_ms"], 0)
        self.assertTrue(result["committed_changed"])
        self.assertTrue(result["tentative_changed"])
        self.assertEqual(result["stream_state"], "active")
        self.assertEqual(result["language"]["mode"], "omitted_inapplicable")

    def test_batch_while_stream_active_rejected(self):
        engine = self.make_engine()
        engine.start_stream()
        with self.assertRaises(backend.EngineStateError):
            engine.transcribe([0.0] * 160)
        self.assertEqual(self.owner.run_calls, 0)

    def test_start_new_stream_after_finalize_resets_previous(self):
        engine = self.make_engine()
        engine.start_stream()
        engine.feed([0.0] * 16, final=True)
        engine.start_stream()
        self.assertEqual(len(self.owner.streams), 2)
        self.assertEqual(self.owner.streams[0].reset_calls, 1)
        self.assertEqual(self.owner.streams[1].state, "active")

    def test_failed_finalize_marks_stream_failed_and_recoverable(self):
        engine = self.make_engine()
        engine.start_stream()
        self.owner.fail_finalize = True
        with self.assertRaises(backend.EngineError):
            engine.feed([0.0] * 16, final=True)
        with self.assertRaises(backend.EngineStateError):
            engine.feed([0.0] * 16)
        self.owner.fail_finalize = False
        engine.start_stream()
        self.assertEqual(self.owner.streams[0].reset_calls, 1)
        self.assertEqual(self.owner.streams[1].state, "active")

    def test_terminal_feed_error_marks_failed_and_allows_restart_or_batch(self):
        engine = self.make_engine()
        engine.start_stream()
        self.owner.fail_feed = True
        with self.assertRaises(backend.EngineError):
            engine.feed([0.0] * 16)
        with self.assertRaises(backend.EngineStateError):
            engine.feed([0.0] * 16)
        # A terminal native feed failure released the stream lease; the
        # adapter must not keep reporting an active stream or require another
        # failing flush before recovery.
        self.owner.fail_feed = False
        engine.transcribe([0.0] * 160)
        engine.start_stream()
        self.assertEqual(self.owner.streams[0].reset_calls, 1)
        self.assertEqual(self.owner.streams[1].state, "active")

    def test_terminal_final_feed_error_marks_failed_and_allows_restart(self):
        engine = self.make_engine()
        engine.start_stream()
        self.owner.fail_feed = True
        with self.assertRaises(backend.EngineError):
            engine.feed([0.0] * 16, final=True)
        self.owner.fail_feed = False
        engine.start_stream()
        self.assertEqual(self.owner.streams[0].reset_calls, 1)
        self.assertEqual(self.owner.streams[1].state, "active")

    def test_nonfinal_snapshot_error_marks_failed_and_allows_restart(self):
        engine = self.make_engine()
        engine.start_stream()
        self.owner.fail_snapshot = "failed"
        with self.assertRaises(backend.EngineError) as caught:
            engine.feed([0.0] * 16)
        self.assertIn("snapshot", str(caught.exception))
        self.assertIn("failed", str(caught.exception))
        self.owner.fail_snapshot = None
        with self.assertRaises(backend.EngineStateError):
            engine.feed([0.0] * 16)
        engine.start_stream()
        self.assertEqual(self.owner.streams[0].reset_calls, 1)
        self.assertEqual(self.owner.streams[1].state, "active")

    def test_nonfinal_text_view_error_marks_failed_and_allows_restart(self):
        engine = self.make_engine()
        engine.start_stream()
        self.owner.fail_text_view = "failed"
        with self.assertRaises(backend.EngineError) as caught:
            engine.feed([0.0] * 16)
        self.assertIn("text_views", str(caught.exception))
        self.assertIn("failed", str(caught.exception))
        self.owner.fail_text_view = None
        engine.start_stream()
        self.assertEqual(self.owner.streams[0].reset_calls, 1)
        self.assertEqual(self.owner.streams[1].state, "active")

    def test_nonfinal_snapshot_error_active_state_remains_retryable(self):
        engine = self.make_engine()
        engine.start_stream()
        self.owner.fail_snapshot = "active"
        with self.assertRaises(backend.EngineError):
            engine.feed([0.0] * 16)
        self.owner.fail_snapshot = None
        result = engine.feed([0.0] * 16)
        self.assertEqual(result["stream_state"], "active")
        self.assertTrue(result["final"] is False)

    def test_close_after_nonfinal_snapshot_error_resets_failed_stream(self):
        engine = self.make_engine()
        engine.start_stream()
        self.owner.fail_snapshot = "failed"
        with self.assertRaises(backend.EngineError):
            engine.feed([0.0] * 16)
        engine.close()
        self.assertEqual(self.owner.streams[0].reset_calls, 1)
        self.assertTrue(self.owner.model_closed)

    def test_close_is_idempotent_and_blocks_compute(self):
        engine = self.make_engine()
        engine.close()
        engine.close()
        with self.assertRaises(backend.EngineClosedError):
            engine.transcribe([0.0] * 160)
        with self.assertRaises(backend.EngineClosedError):
            engine.start_stream()
        with self.assertRaises(backend.EngineClosedError):
            engine.feed([0.0])
        info = engine.info
        self.assertTrue(info["closed"])
        self.assertTrue(self.owner.model_closed)

    def test_close_active_stream_resets_and_closes_everything(self):
        engine = self.make_engine()
        engine.start_stream()
        engine.close()
        self.assertEqual(self.owner.streams[0].reset_calls, 1)
        self.assertTrue(all(session.closed for session in self.owner.sessions))
        self.assertTrue(self.owner.model_closed)

    def test_close_after_error_is_safe_and_reports_close_error(self):
        engine = self.make_engine()
        stream = None
        engine.start_stream()
        stream = self.owner.streams[0]

        def fail_reset():
            raise RuntimeError("reset failed")

        stream.reset = fail_reset
        engine.close()
        self.assertTrue(engine.info["closed"])
        self.assertTrue(any(error.startswith("stream:") for error in engine.info["close_errors"]))
        self.assertTrue(self.owner.model_closed)

    # ------------------------------------------------------------------
    # streaming capability and parameters
    # ------------------------------------------------------------------
    def test_unsupported_native_stream_never_falls_back_to_batch(self):
        self.owner.capabilities.supports_streaming = False
        engine = self.make_engine()
        with self.assertRaises(backend.UnsupportedCapability):
            engine.start_stream()
        self.assertEqual(self.owner.stream_begin_calls, 0)
        self.assertEqual(self.owner.run_calls, 0)

    def test_context_policy_and_cadence_are_recorded(self):
        engine = self.make_engine()
        engine.start_stream(
            feed_chunk_ms=1120,
            att_context_right_frames=13,
            commit_policy="stable-prefix",
            agreement_n=2,
        )
        call = self.owner.sessions[-1].stream_calls[0]
        self.assertEqual(call["commit_policy"], "stable_prefix")
        self.assertEqual(call["stable_prefix_agreement_n"], 2)
        self.assertEqual(call["timestamps"], "none")
        self.assertNotIn("feed_chunk_ms", call)
        self.assertIsNotNone(call.get("family"))
        self.assertEqual(call["family"].att_context_right, 13)
        meta = engine._stream_meta
        self.assertEqual(meta["feed_chunk_ms"], 1120)
        self.assertEqual(
            meta["att_context"]["att_context_right_frames_requested"], 13
        )
        self.assertEqual(meta["att_context"]["att_context_right_frames_applied"], 13)
        self.assertIsNone(meta["att_context"]["att_context_right_frames_accepted"])
        self.assertIsNone(
            meta["att_context"]["model_default_att_context_right_frames"]
        )
        self.assertEqual(meta["att_context"]["applied_context_source"], "native")
        self.assertIn(
            "succeeded",
            meta["att_context"]["applied_context_evidence"],
        )
        self.assertEqual(
            meta["att_context"]["reason"], "applied_native_begin_accepted"
        )

    def test_model_without_parakeet_extension_fails_closed(self):
        self.owner.accepts_parakeet_stream = False
        engine = self.make_engine()
        with self.assertRaises(backend.UnsupportedCapability) as caught:
            engine.start_stream(att_context_right_frames=3)
        self.assertIn("does not accept", str(caught.exception))
        self.assertEqual(self.owner.stream_begin_calls, 0)
        info = engine.info
        self.assertEqual(info["native_stream"]["att_context_right_frames_requested"], 3)
        self.assertIsNone(info["native_stream"]["att_context_right_frames_applied"])
        self.assertIsNone(info["native_stream"]["att_context_right_frames_accepted"])
        self.assertIsNone(info["native_stream"]["model_default_att_context_right_frames"])
        self.assertEqual(
            info["native_stream"]["applied_context_source"], "unavailable"
        )
        self.assertEqual(
            info["native_stream"]["reason"],
            "model_does_not_accept_parakeet_stream_extension",
        )
        self.assertIn(
            "not applied",
            info["native_stream"]["applied_context_evidence"],
        )
        self.assertTrue(info["capabilities"]["batch"])

    def test_stream_context_metadata_exposed_in_info_and_results(self):
        engine = self.make_engine()
        engine.start_stream(att_context_right_frames=3)
        info = engine.info
        self.assertEqual(info["stream_contract"]["att_context_right_frames_default"], 3)
        self.assertFalse(
            info["stream_contract"]["att_context_right_frames_default_is_model_default"]
        )
        self.assertEqual(
            info["stream_contract"]["att_context_right_frames_requested"], 3
        )
        self.assertEqual(info["stream_contract"]["att_context_right_frames_applied"], 3)
        self.assertIsNone(
            info["stream_contract"]["att_context_right_frames_accepted"]
        )
        self.assertIsNone(
            info["stream_contract"]["model_default_att_context_right_frames"]
        )
        self.assertEqual(
            info["stream_contract"]["applied_context_source"], "native"
        )
        self.assertEqual(info["native_stream"]["att_context_right_frames_requested"], 3)
        self.assertEqual(info["native_stream"]["att_context_right_frames_applied"], 3)
        self.assertIsNone(info["native_stream"]["att_context_right_frames_accepted"])
        self.assertIsNone(
            info["native_stream"]["model_default_att_context_right_frames"]
        )
        self.assertEqual(info["native_stream"]["applied_context_source"], "native")
        self.assertEqual(info["att_context_right_frames_requested"], 3)
        self.assertEqual(info["att_context_right_frames_applied"], 3)
        self.assertEqual(info["applied_context_source"], "native")

        result = engine.feed([0.1] * 16)
        self.assertEqual(result["att_context_right_frames_requested"], 3)
        self.assertEqual(result["att_context_right_frames_applied"], 3)
        self.assertIsNone(result["att_context_right_frames_accepted"])
        self.assertIsNone(result["att_context_right_frames_model_default"])
        self.assertEqual(result["applied_context_source"], "native")
        self.assertEqual(
            result["native_stream"]["att_context_right_frames_applied"], 3
        )
        self.assertEqual(
            result["native_stream"]["att_context_right_frames_accepted"], None
        )
        self.assertEqual(
            result["native_stream"]["model_default_att_context_right_frames"], None
        )
        self.assertNotEqual(
            result["att_context_right_frames_model_default"],
            result["att_context_right_frames_requested"],
        )

    def test_minus_one_context_reports_null_applied_not_guessed_default(self):
        engine = self.make_engine()
        engine.start_stream(att_context_right_frames=-1)
        info = engine.info
        self.assertEqual(info["native_stream"]["att_context_right_frames_requested"], -1)
        self.assertIsNone(info["native_stream"]["att_context_right_frames_applied"])
        self.assertEqual(
            info["native_stream"]["applied_context_source"], "unavailable"
        )
        self.assertEqual(
            info["native_stream"]["reason"], "model_default_requested_not_exposed"
        )
        self.assertIsNone(
            info["native_stream"]["model_default_att_context_right_frames"]
        )
        result = engine.feed([0.1] * 16)
        self.assertEqual(result["att_context_right_frames_requested"], -1)
        self.assertIsNone(result["att_context_right_frames_applied"])
        self.assertEqual(result["applied_context_source"], "unavailable")
        self.assertIsNone(result["att_context_right_frames_model_default"])

    def test_native_begin_rejection_records_context_attempt(self):
        self.owner.reject_stream_begin = True
        engine = self.make_engine()
        with self.assertRaises(backend.EngineError):
            engine.start_stream(att_context_right_frames=3)
        info = engine.info
        self.assertEqual(info["native_stream"]["att_context_right_frames_requested"], 3)
        self.assertIsNone(info["native_stream"]["att_context_right_frames_applied"])
        self.assertEqual(
            info["native_stream"]["applied_context_source"], "unavailable"
        )
        self.assertEqual(info["native_stream"]["reason"], "native_begin_rejected")
        self.assertEqual(self.owner.run_calls, 0)

    def test_native_begin_rejection_is_clear_and_not_batch_fallback(self):
        self.owner.reject_stream_begin = True
        engine = self.make_engine()
        with self.assertRaises(backend.EngineError) as caught:
            engine.start_stream(att_context_right_frames=3)
        message = str(caught.exception)
        self.assertIn("att_context_right_frames=3", message)
        self.assertIn("model-specific", message)
        self.assertIn("{0,3,6,13}", message)
        self.assertEqual(self.owner.run_calls, 0)
        self.owner.reject_stream_begin = False
        engine.start_stream(att_context_right_frames=13)
        self.assertEqual(self.owner.streams[0].kwargs["family"].att_context_right, 13)

    def test_stream_parameter_validation(self):
        engine = self.make_engine()
        invalid = [
            {"feed_chunk_ms": 0},
            {"feed_chunk_ms": -1},
            {"feed_chunk_ms": float("nan")},
            {"att_context_right_frames": -2},
            {"att_context_right_frames": 3.5},
            {"att_context_right_frames": True},
            {"agreement_n": 0},
            {"agreement_n": True},
            {"commit_policy": "unknown"},
        ]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                engine.start_stream(**kwargs)
        self.assertEqual(self.owner.stream_begin_calls, 0)

    def test_commit_policy_aliases(self):
        engine = self.make_engine()
        for requested, native in (
            ("stable_prefix", "stable_prefix"),
            ("auto", "auto"),
            ("on-finalize", "on_finalize"),
        ):
            engine.start_stream(commit_policy=requested)
            self.assertEqual(
                self.owner.sessions[-1].stream_calls[-1]["commit_policy"], native
            )
            engine.feed([0.0] * 16, final=True)

    def test_explicit_stream_language_mapping(self):
        engine = self.make_engine()
        engine.start_stream(language="es-MX")
        call = self.owner.sessions[-1].stream_calls[0]
        self.assertEqual(call["language"], "es")
        self.assertEqual(engine._stream_meta["language"]["mapping"], "primary_subtag")

    # ------------------------------------------------------------------
    # backend honesty
    # ------------------------------------------------------------------
    def test_backend_unknown_is_reported_honestly(self):
        self.owner.model_backend = ""
        self.owner.device_raises = True
        engine = self.make_engine()
        info = engine.info
        self.assertEqual(info["backend"]["reported_backend"], "unknown")
        self.assertFalse(info["backend"]["device"]["available"])
        self.assertEqual(info["backend"]["device"]["reason"], "RuntimeError")

    def test_use_gpu_false_requests_cpu_policy(self):
        engine = self.make_engine(use_gpu=False)
        info = engine.info
        self.assertEqual(info["backend"]["requested_policy"], "cpu")
        self.assertEqual(info["backend"]["reported_backend"], "cpu")
        self.assertEqual(self.owner.models[0].backend, "cpu")

    # ------------------------------------------------------------------
    # library discovery and integrity guards
    # ------------------------------------------------------------------
    def test_discovery_is_project_local_and_ordered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / ".tools" / "build" / "src" / "libtranscribe.dylib"
            bin_path = root / ".tools" / "build" / "bin" / "libtranscribe.dylib"
            src.parent.mkdir(parents=True)
            bin_path.parent.mkdir(parents=True)
            src.write_bytes(b"src")
            bin_path.write_bytes(b"bin")
            self.assertEqual(backend.discover_library(root), src)
            (root / "native").mkdir()
            native = root / "native" / "libtranscribe.dylib"
            native.write_bytes(b"native")
            self.assertEqual(backend.discover_library(root), native)
            with mock.patch.dict(os.environ, {"TRANSCRIBE_LIBRARY": "/tmp/not-here"}):
                self.assertEqual(backend.discover_library(root), native)

        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                backend.resolve_library_path(None, root=empty)

    def test_explicit_library_path_file_or_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "libtranscribe.dylib"
            library.write_bytes(b"x")
            self.assertEqual(backend.resolve_library_path(library), library.resolve())
            self.assertEqual(backend.resolve_library_path(root), library.resolve())
            with self.assertRaises(FileNotFoundError):
                backend.resolve_library_path(root / "missing.dylib")

    def test_load_binding_restores_env_and_sys_path_and_verifies_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            write_fake_binding_package(src)
            library = root / "libtranscribe.dylib"
            library.write_bytes(b"fake")
            record = root / "record.json"
            before_env = os.environ.get("TRANSCRIBE_LIBRARY")
            old_path = list(sys.path)
            drop_transcribe_modules()
            try:
                with mock.patch.object(backend, "_BINDING_SRC", src), mock.patch.object(
                    backend, "_BINDING_MODULE", None
                ), mock.patch.object(backend, "_BINDING_LIBRARY", None), mock.patch.dict(
                    os.environ,
                    {
                        "TRANSCRIBE_LIBRARY": "sentinel-before",
                        "FAKE_BINDING_RECORD": str(record),
                    },
                ):
                    loaded = self._real_load_binding(library)
                    env_after_call = os.environ.get("TRANSCRIBE_LIBRARY")
                payload = json.loads(record.read_text())
                self.assertEqual(
                    Path(payload["package"]), (src / "transcribe_cpp" / "__init__.py").resolve()
                )
                self.assertEqual(payload["env"], str(library.resolve()))
                self.assertEqual(env_after_call, "sentinel-before")
                self.assertEqual(os.environ.get("TRANSCRIBE_LIBRARY"), before_env)
                self.assertEqual(sys.path, old_path)
                self.assertEqual(Path(loaded.library_path()), library.resolve())
            finally:
                drop_transcribe_modules()
                if before_env is None:
                    os.environ.pop("TRANSCRIBE_LIBRARY", None)
                else:
                    os.environ["TRANSCRIBE_LIBRARY"] = before_env

    def test_load_binding_rejects_preimported_module_from_other_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_a = root / "src-a"
            src_b = root / "src-b"
            write_fake_binding_package(src_a)
            write_fake_binding_package(src_b)
            library = root / "libtranscribe.dylib"
            library.write_bytes(b"fake")
            before_env = os.environ.get("TRANSCRIBE_LIBRARY")
            drop_transcribe_modules()
            old_path = list(sys.path)
            try:
                os.environ["TRANSCRIBE_LIBRARY"] = str(library.resolve())
                sys.path.insert(0, str(src_a))
                import transcribe_cpp  # noqa: F401

                self.assertEqual(
                    Path(transcribe_cpp.__file__).resolve().parent,
                    (src_a / "transcribe_cpp").resolve(),
                )
                with mock.patch.object(backend, "_BINDING_SRC", src_b), mock.patch.object(
                    backend, "_BINDING_MODULE", None
                ), mock.patch.object(backend, "_BINDING_LIBRARY", None):
                    with self.assertRaises(backend.EngineError) as caught:
                        self._real_load_binding(library)
                self.assertIn("source", str(caught.exception).lower())
            finally:
                drop_transcribe_modules()
                if before_env is None:
                    os.environ.pop("TRANSCRIBE_LIBRARY", None)
                else:
                    os.environ["TRANSCRIBE_LIBRARY"] = before_env
                sys.path[:] = old_path

    def test_load_binding_rejects_reported_library_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            other = root / "other.dylib"
            other.write_bytes(b"other")
            write_fake_binding_package(src, reported_library=str(other))
            library = root / "libtranscribe.dylib"
            library.write_bytes(b"fake")
            drop_transcribe_modules()
            try:
                with mock.patch.object(backend, "_BINDING_SRC", src), mock.patch.object(
                    backend, "_BINDING_MODULE", None
                ), mock.patch.object(backend, "_BINDING_LIBRARY", None):
                    with self.assertRaises(backend.EngineError):
                        self._real_load_binding(library)
            finally:
                drop_transcribe_modules()

    def test_load_binding_import_failure_cleans_modules_and_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            write_fake_binding_package(src, raises=True)
            library = root / "libtranscribe.dylib"
            library.write_bytes(b"fake")
            before_env = os.environ.get("TRANSCRIBE_LIBRARY")
            old_path = list(sys.path)
            drop_transcribe_modules()
            try:
                with mock.patch.object(backend, "_BINDING_SRC", src), mock.patch.object(
                    backend, "_BINDING_MODULE", None
                ), mock.patch.object(backend, "_BINDING_LIBRARY", None):
                    with self.assertRaises(backend.EngineError):
                        self._real_load_binding(library)
                self.assertNotIn("transcribe_cpp", sys.modules)
                self.assertEqual(os.environ.get("TRANSCRIBE_LIBRARY"), before_env)
                self.assertEqual(sys.path, old_path)
            finally:
                drop_transcribe_modules()
                if before_env is None:
                    os.environ.pop("TRANSCRIBE_LIBRARY", None)
                else:
                    os.environ["TRANSCRIBE_LIBRARY"] = before_env

    def test_library_artifact_hash_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".tools" / "build" / "src" / "libtranscribe.dylib"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"pinned library bytes")
            digest = backend._sha256_file(artifact)
            lock = fake_lock(
                artifact={
                    "path": ".tools/build/src/libtranscribe.dylib",
                    "sha256": digest,
                    "size_bytes": artifact.stat().st_size,
                }
            )
            with mock.patch.object(backend, "_SPIKE_ROOT", root):
                record = backend.verify_library_artifact(artifact, lock)
                self.assertTrue(record["verified"])
                artifact.write_bytes(b"tampered library bytes")
                with self.assertRaises(backend.EngineError):
                    backend.verify_library_artifact(artifact, lock)

    def test_lock_validation_and_native_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "lock.json"
            path.write_text(json.dumps({"schema_version": 1, "engine": {}, "artifact": {}}))
            with self.assertRaises(backend.EngineError):
                self._real_load_lock(path)
            path.write_text(json.dumps({"schema_version": 2}))
            with self.assertRaises(backend.EngineError):
                self._real_load_lock(path)
            path.write_text(json.dumps(fake_lock()))
            self.assertEqual(self._real_load_lock(path)["engine"]["version"], "0.4.1")

        lock = fake_lock()
        good = types.SimpleNamespace(
            native_version=lambda: "0.4.1",
            native_commit=lambda: "8facde6",
        )
        self.assertTrue(backend.verify_native_identity(good, lock)["verified"])
        bad_version = types.SimpleNamespace(
            native_version=lambda: "0.4.2",
            native_commit=lambda: "8facde6",
        )
        with self.assertRaises(backend.EngineError):
            backend.verify_native_identity(bad_version, lock)
        bad_commit = types.SimpleNamespace(
            native_version=lambda: "0.4.1",
            native_commit=lambda: "unknown",
        )
        with self.assertRaises(backend.EngineError):
            backend.verify_native_identity(bad_commit, lock)
        binding_lock = fake_lock(
            engine={
                "repository": "https://github.com/handy-computer/transcribe.cpp",
                "revision": "8facde6fcd8fb9caa585a5788ab450df6e8ec7db",
                "version": "0.4.1",
                "python_binding": {"version": "0.4.1"},
            }
        )
        with_version = types.SimpleNamespace(
            native_version=lambda: "0.4.1",
            native_commit=lambda: "8facde6",
            __version__="0.4.1",
        )
        self.assertTrue(backend.verify_native_identity(with_version, binding_lock)["verified"])
        bad_binding_version = types.SimpleNamespace(
            native_version=lambda: "0.4.1",
            native_commit=lambda: "8facde6",
            __version__="0.4.2",
        )
        with self.assertRaises(backend.EngineError):
            backend.verify_native_identity(bad_binding_version, binding_lock)


# ---------------------------------------------------------------------------
# build-script source pin guard
# ---------------------------------------------------------------------------
def load_build_engine_module():
    path = TOOLS_DIR / "build_engine.py"
    spec = importlib.util.spec_from_file_location("build_engine_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def make_temp_engine_repo(root: Path):
    (root / "include").mkdir(parents=True)
    (root / "bindings" / "python" / "src" / "transcribe_cpp").mkdir(parents=True)
    (root / "ggml").mkdir()
    (root / "patches" / "ggml").mkdir(parents=True)
    (root / "include" / "transcribe.h").write_text(
        "#define TRANSCRIBE_VERSION_MAJOR 0\n"
        "#define TRANSCRIBE_VERSION_MINOR 4\n"
        "#define TRANSCRIBE_VERSION_PATCH 1\n",
        encoding="utf-8",
    )
    (root / "bindings" / "python" / "src" / "transcribe_cpp" / "__init__.py").write_text(
        '__version__ = "0.4.1"\n', encoding="utf-8"
    )
    (root / "include" / "transcribe.abihash").write_text(
        "f99ad4169374b8f3\n", encoding="utf-8"
    )
    (root / "patches" / "ggml" / "0001-fix.patch").write_text(
        "patch-body\n", encoding="utf-8"
    )
    (root / "ggml" / "UPSTREAM").write_text(
        "repo: git@github.com:ggml-org/ggml.git\n"
        "sha:  d7cb574130e6f01ad25b3289685489200febcd74\n"
        "patches:\n"
        "  patches/ggml/0001-fix.patch\n"
        "\n"
        "This directory is generated; prose must not be parsed as a patch.\n",
        encoding="utf-8",
    )
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "fixture")
    head = git(root, "rev-parse", "HEAD")
    ggml_tree = git(root, "rev-parse", "HEAD:ggml")
    patch_tree = git(root, "rev-parse", "HEAD:patches")
    return head, ggml_tree, patch_tree


class PinGuardTestCase(unittest.TestCase):
    def setUp(self):
        self.build_engine = load_build_engine_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "engine"
        self.repo.mkdir()
        self.head, self.ggml_tree, self.patch_tree = make_temp_engine_repo(self.repo)

    def verify(self, **overrides):
        kwargs = {
            "expected_revision": self.head,
            "expected_version": "0.4.1",
            "expected_ggml_sha": "d7cb574130e6f01ad25b3289685489200febcd74",
            "expected_ggml_tree": self.ggml_tree,
            "expected_patch_tree": self.patch_tree,
            "verify_remote": False,
        }
        kwargs.update(overrides)
        return self.build_engine.verify_checkout(self.repo, **kwargs)

    def test_clean_pin_passes(self):
        record = self.verify()
        self.assertEqual(record["revision"], self.head)
        self.assertEqual(record["ggml"]["patches"][0]["path"],
                         "patches/ggml/0001-fix.patch")
        self.assertTrue(record["clean_tree_verified"])

    def test_dirty_tamper_fails(self):
        with open(self.repo / "include" / "transcribe.h", "a", encoding="utf-8") as handle:
            handle.write("/* tampered */\n")
        with self.assertRaises(self.build_engine.BuildError) as caught:
            self.verify()
        self.assertIn("dirty", str(caught.exception))

    def test_wrong_revision_fails(self):
        with open(self.repo / "include" / "transcribe.h", "a", encoding="utf-8") as handle:
            handle.write("/* next revision */\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "next")
        with self.assertRaises(self.build_engine.BuildError) as caught:
            self.verify()
        self.assertIn("revision mismatch", str(caught.exception))

    def test_tampered_ggml_tree_or_sha_fails(self):
        with self.assertRaises(self.build_engine.BuildError):
            self.verify(expected_ggml_tree="0" * 40)
        with self.assertRaises(self.build_engine.BuildError):
            self.verify(expected_ggml_sha="1" * 40)
        with self.assertRaises(self.build_engine.BuildError):
            self.verify(expected_patch_tree="2" * 40)

    def test_tampered_patch_file_fails_even_if_committed(self):
        (self.repo / "patches" / "ggml" / "0001-fix.patch").write_text(
            "tampered-body\n", encoding="utf-8"
        )
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "tampered patch")
        with self.assertRaises(self.build_engine.BuildError) as caught:
            self.verify(expected_revision=git(self.repo, "rev-parse", "HEAD"))
        self.assertIn("patch tree mismatch", str(caught.exception))

    def test_lock_source_drift_fails(self):
        record = self.verify()
        lock = {
            "schema_version": 1,
            "engine": {
                "repository": record["repository"],
                "revision": record["revision"],
                "version": record["version"],
                "abi_hash": record["abi_hash"],
                "python_binding": {"version": record["python_binding_version"]},
            },
            "source_verification": {"ggml": record["ggml"]},
        }
        lock_path = Path(self.tmp.name) / "engine.lock.json"
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        self.build_engine.verify_lock_source_pin(record, lock_path)
        lock["engine"]["revision"] = "0" * 40
        lock_path.write_text(json.dumps(lock), encoding="utf-8")
        with self.assertRaises(self.build_engine.BuildError) as caught:
            self.build_engine.verify_lock_source_pin(record, lock_path)
        self.assertIn("engine lock/source drift", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
