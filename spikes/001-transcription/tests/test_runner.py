"""Deterministic replay-runner, manifest, scheduler and result-integrity tests.

All tests use fake engines and fake clocks; no model, native helper, network or
audio hardware is required.
"""

from __future__ import annotations

import array
import hashlib
import json
import math
import os
import sys
import unittest
import wave
from pathlib import Path

SPIKE_ROOT = Path(__file__).resolve().parents[1]
if str(SPIKE_ROOT) not in sys.path:
    sys.path.insert(0, str(SPIKE_ROOT))

import run  # noqa: E402


# ---------------------------------------------------------------------------
# Deterministic doubles
# ---------------------------------------------------------------------------


class FakeBatchEngine:
    def __init__(
        self,
        clock: "run.FakeClock",
        *,
        decode_s: float = 0.0,
        text_fn=None,
        texts: list[str] | None = None,
        tokens: list[dict] | None = None,
        fail_on_call: int | None = None,
        hints: dict | None = None,
        decode_ms: float | None = None,
    ) -> None:
        self.clock = clock
        self.decode_s = decode_s
        self.text_fn = text_fn
        self.texts = texts
        self.tokens = tokens or []
        self.fail_on_call = fail_on_call
        self.hints = hints or {}
        self.decode_ms = decode_ms
        self.calls: list[dict] = []

    def transcribe(self, samples, *, sample_rate: int = 16000, language=None) -> dict:
        index = len(self.calls)
        self.calls.append(
            {
                "samples": len(samples),
                "now": self.clock.now(),
                "sample_rate": sample_rate,
                "language": language,
            }
        )
        if self.fail_on_call == index:
            raise RuntimeError("synthetic decode failure")
        self.clock.advance(self.decode_s)
        if self.text_fn is not None:
            text = self.text_fn(len(samples), index)
        elif self.texts is not None:
            text = self.texts[min(index, len(self.texts) - 1)]
        else:
            text = "alpha beta"
        result = {
            "text": text,
            "tokens": list(self.tokens),
            "decode_ms": self.decode_ms,
            "final": False,
        }
        result.update(self.hints)
        return result


class FakeStreamEngine:
    def __init__(
        self,
        clock: "run.FakeClock",
        *,
        feed_s: float = 0.0,
        commits: list[str] | None = None,
        finals: list[str | None] | None = None,
        fail_on_call: int | None = None,
        info_override: dict | None = None,
    ) -> None:
        self.clock = clock
        self.feed_s = feed_s
        self.commits = commits or []
        self.finals = finals or []
        self.fail_on_call = fail_on_call
        self.info_override = info_override
        self.start_calls: list[dict] = []
        self._fed: list[float] = []
        self._feed_calls: list[dict] = []
        self.history: list[list[float]] = []
        self.feed_calls_history: list[list[dict]] = []
        self._active = False

    @property
    def feed_calls(self) -> list[dict]:
        return list(self._feed_calls)

    @property
    def info(self) -> dict:
        if self.info_override is not None:
            return self.info_override
        return {
            "capabilities": {"batch": True, "native_stream": True, "timestamps": True},
            "native_stream": {
                "att_context_right_frames_default": 3,
                "att_context_right_frames_requested": 3,
                "att_context_right_frames_applied": 3,
                "att_context_right_frames_accepted": None,
                "model_default_att_context_right_frames": None,
                "applied_context_source": "native",
                "att_context_reason": "applied_native_begin_accepted",
            },
            "stream_contract": {
                "att_context_right_frames_default": 3,
                "att_context_right_frames_default_is_model_default": False,
                "att_context_right_frames_default_evidence": (
                    "Engine API default; not model-default evidence"
                ),
            },
        }

    def start_stream(self, **kwargs) -> None:
        self.start_calls.append(kwargs)
        self._fed = []
        self._feed_calls = []
        self.history.append([])
        self.feed_calls_history.append([])
        self._active = True

    def feed(self, samples, *, final: bool = False) -> dict:
        if not self._active:
            raise RuntimeError("feed before start_stream")
        index = len(self._feed_calls)
        self._feed_calls.append({"samples": len(samples), "final": final, "now": self.clock.now()})
        self.feed_calls_history[-1] = list(self._feed_calls)
        self._fed.extend(float(v) for v in samples)
        self.history[-1] = list(self._fed)
        self.clock.advance(self.feed_s)
        if self.fail_on_call == index:
            raise RuntimeError("synthetic stream failure")
        text = " ".join(f"w{i}" for i in range(len(self._fed) // 1600))
        committed = self.commits[index] if index < len(self.commits) else ""
        final_text = self.finals[index] if index < len(self.finals) else (text if final else None)
        return {
            "text": text,
            "tokens": [],
            "decode_ms": None,
            "final": final,
            "committed_text": committed,
            "tentative_text": "",
            "display_text": text,
            "final_text": final_text,
        }

    def close(self) -> None:
        self._active = False


def make_fixture(
    seconds: float = 1.0,
    *,
    fixture_id: str = "tiny",
    segments: list["run.Segment"] | None = None,
    reference: str = "alpha beta",
    sample_rate: int = 16000,
) -> "run.Fixture":
    count = int(round(seconds * sample_rate))
    samples = array.array("d", [0.25] * count)
    if segments is None:
        segments = [run.Segment(0.0, seconds, "oracle_file_boundary")]
    return run.Fixture(
        id=fixture_id,
        language="en",
        asr_language="en-US",
        wav_relative=f"fixtures/{fixture_id}.wav",
        reference_relative=f"fixtures/{fixture_id}.txt",
        wav_path=Path("fixtures") / f"{fixture_id}.wav",
        reference_path=Path("fixtures") / f"{fixture_id}.txt",
        wav_sha256="a" * 64,
        reference_sha256="b" * 64,
        duration_s=seconds,
        samples=samples,
        sample_rate=sample_rate,
        reference_text=reference,
        source={
            "url": "https://example.org/public-data",
            "revision": "70bb2e84b976b7e960aa89f1c648e09c59f894dd",
            "license": "CC-BY-4.0",
            "config": "en_us",
            "locale": "en_us",
            "split": "test",
            "row": 0,
            "item_id": f"{fixture_id}.wav",
            "audio_sha256": "c" * 64,
            "reference_column": "raw_transcription",
        },
        conversion={"tool": "none"},
        segments=segments,
    )


def hybrid_config(**overrides) -> "run.ReplayConfig":
    values = dict(
        arm="hybrid",
        clock_mode="fake",
        partial_interval_ms=1000,
        feed_chunk_ms=1000,
        max_window_ms=20000,
        right_context_frames=3,
    )
    values.update(overrides)
    return run.ReplayConfig(**values)


# ---------------------------------------------------------------------------
# Scheduler and arms
# ---------------------------------------------------------------------------


class HybridSchedulerTests(unittest.TestCase):
    def test_never_requests_future_audio_and_coalesces_slow_ticks(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(clock, decode_s=3.5)
        runner = run.ReplayRunner(engine, clock, hybrid_config(partial_interval_ms=1000, max_window_ms=5000))
        fixture = make_fixture(5.0)

        trial = runner.run(fixture, phase="measured", trial_index=0, repeat_index=0)

        partials = [event for event in trial["events"] if event["kind"] == "partial"]
        self.assertEqual(len(partials), 2)

        first, second = partials
        self.assertEqual(first["selected_tick"], 1)
        self.assertEqual(first["timing"]["frozen_prefix_samples"], 16000)
        self.assertEqual(first["timing"]["arrived_samples"], 16000)
        self.assertEqual(first["coalesced_ticks"], [2, 3])
        self.assertEqual(first["timing"]["queue_lag_ms"], 0.0)

        self.assertEqual(second["selected_tick"], 4)
        self.assertEqual(second["timing"]["frozen_prefix_samples"], 64000)
        self.assertEqual(second["timing"]["arrived_samples"], 72000)
        self.assertEqual(second["timing"]["backlog_samples"], 8000)
        self.assertEqual(second["timing"]["queue_lag_ms"], 500.0)

        final = trial["events"][-1]
        self.assertEqual(final["kind"], "final")
        self.assertEqual(final["timing"]["frozen_prefix_samples"], 80000)
        self.assertEqual(final["timing"]["arrived_samples"], 80000)
        self.assertEqual(final["timing"]["backlog_samples"], 0)

        for event in trial["events"]:
            timing = event["timing"]
            self.assertLessEqual(
                timing["frozen_prefix_samples"],
                timing["arrived_samples"],
                "a decode must never see samples that have not arrived",
            )
        for call in engine.calls:
            self.assertLessEqual(call["samples"], math.floor(call["now"] * 16000))

        self.assertEqual(trial["timings"]["measured"], None)
        self.assertEqual(trial["timings"]["simulated"]["first_partial_ms"], 4500.0)
        self.assertEqual(trial["timings"]["simulated"]["first_stable_ms"], 8000.0)
        self.assertEqual(trial["timings"]["simulated"]["final_after_audio_end_ms"], 6500.0)
        self.assertEqual(trial["timings"]["simulated"]["coalesced_ticks"], 2)

    def test_finalization_is_prioritized_after_a_very_slow_partial(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(clock, decode_s=5.5)
        runner = run.ReplayRunner(engine, clock, hybrid_config(partial_interval_ms=1000, max_window_ms=5000))
        trial = runner.run(make_fixture(5.0), phase="measured", trial_index=0, repeat_index=0)

        partials = [event for event in trial["events"] if event["kind"] == "partial"]
        self.assertEqual(len(partials), 1)
        self.assertEqual(partials[0]["selected_tick"], 1)
        self.assertEqual(partials[0]["timing"]["call_end_ms"], 6500.0)

        final = trial["events"][-1]
        self.assertEqual(final["kind"], "final")
        self.assertEqual(final["coalesced_ticks"], [2, 3, 4])
        self.assertGreaterEqual(final["timing"]["call_start_ms"], partials[0]["timing"]["call_end_ms"])
        self.assertEqual(final["timing"]["frozen_prefix_samples"], 80000)

    def test_partial_text_and_stable_conflict_are_retained(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(clock, decode_s=0.0, texts=["alpha beta", "alpha beta", "alpha zeta"])
        runner = run.ReplayRunner(engine, clock, hybrid_config(partial_interval_ms=1000, max_window_ms=5000))
        trial = runner.run(make_fixture(4.0), phase="measured", trial_index=0, repeat_index=0)

        partials = [event for event in trial["events"] if event["kind"] == "partial"]
        self.assertEqual(partials[1]["policy"]["stable_text"], "alpha beta")
        self.assertIsNotNone(partials[2]["policy"]["conflict"])
        self.assertEqual(trial["texts"]["stable_raw"], "alpha beta")
        self.assertEqual(len(trial["conflicts"]), 1)
        self.assertEqual(len(trial["stable_history"]), 2)

    def test_zero_and_negative_native_decode_ms_are_unknown(self) -> None:
        for value in (0.0, -3.0, float("nan")):
            with self.subTest(value=value):
                clock = run.FakeClock(0.0)
                engine = FakeBatchEngine(clock, decode_s=0.0, decode_ms=value)
                runner = run.ReplayRunner(engine, clock, hybrid_config(max_window_ms=2000))
                trial = runner.run(
                    make_fixture(1.0), phase="measured", trial_index=0, repeat_index=0
                )
                final_event = trial["events"][-1]
                self.assertIsNone(final_event["decode_ms"])
                native_decode = trial["timings"]["simulated"]["native_decode_ms"]
                self.assertEqual(native_decode["known_values"], 0)
                self.assertEqual(native_decode["unknown_values"], 1)
                self.assertIsNone(native_decode["total_ms"])

    def test_engine_error_records_error_trial_without_fabricated_metrics(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(clock, fail_on_call=0)
        runner = run.ReplayRunner(engine, clock, hybrid_config())
        trial = runner.run(make_fixture(1.0), phase="measured", trial_index=0, repeat_index=0)
        self.assertEqual(trial["status"], "error")
        self.assertIsNone(trial["wer"])
        self.assertIsNone(trial["timings"])
        self.assertEqual(trial["events"], [])
        self.assertIn("synthetic decode failure", trial["error"]["message"])
        self.assertFalse(trial["fatal_stream_state"])

    def test_max_window_and_rolling_window_are_rejected(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(clock)
        runner = run.ReplayRunner(engine, clock, hybrid_config(max_window_ms=4000))
        with self.assertRaises(run.UnsupportedWindowError):
            runner.run(make_fixture(5.0), phase="measured", trial_index=0, repeat_index=0)
        default_runner = run.ReplayRunner(engine, clock, hybrid_config())
        with self.assertRaises(run.UnsupportedWindowError):
            default_runner.run(make_fixture(21.0), phase="measured", trial_index=0, repeat_index=0)
        with self.assertRaises(run.UnsupportedWindowError):
            run.ReplayConfig(arm="hybrid", window_mode="rolling")
        with self.assertRaises(ValueError):
            run.ReplayConfig(arm="not-an-arm")


class LanguageHintTests(unittest.TestCase):
    def test_auto_fixture_hint_is_passed_through_without_forcing(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(
            clock,
            decode_s=0.0,
            hints={"resolved_language": "auto", "detected_language": "es"},
        )
        fixture = make_fixture(1.0)
        fixture.asr_language = "auto"
        runner = run.ReplayRunner(engine, clock, hybrid_config())
        trial = runner.run(fixture, phase="measured", trial_index=0, repeat_index=0)

        self.assertEqual(engine.calls[0]["language"], "auto")
        language = trial["language"]
        self.assertEqual(language["requested"], "auto")
        self.assertEqual(language["requested_source"], "fixture.asr_language")
        self.assertEqual(language["engine_default"], "auto")
        self.assertEqual(language["resolved"], "auto")
        self.assertEqual(language["detected"], "es")
        self.assertIn("never forces a first language", language["note"])

    def test_native_stream_receives_auto_hint_unchanged(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(clock, feed_s=0.0, commits=["hola"], finals=["hola"])
        fixture = make_fixture(1.0)
        fixture.asr_language = "auto"
        runner = run.ReplayRunner(
            engine, clock, hybrid_config(arm="native-stream", feed_chunk_ms=1000)
        )
        trial = runner.run(fixture, phase="measured", trial_index=0, repeat_index=0)
        self.assertEqual(engine.start_calls[0]["language"], "auto")
        self.assertEqual(trial["language"]["requested"], "auto")
        self.assertIsNone(trial["language"]["resolved"])


class EndpointArmTests(unittest.TestCase):
    def test_decodes_each_oracle_segment_at_its_boundary(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(clock, decode_s=0.25, texts=["one", "two", "three"])
        config = hybrid_config(arm="endpoint", partial_interval_ms=1000)
        runner = run.ReplayRunner(engine, clock, config)
        fixture = make_fixture(
            3.0,
            segments=[
                run.Segment(0.0, 1.0, "oracle_file_boundary"),
                run.Segment(1.0, 2.0, "oracle_file_boundary"),
                run.Segment(2.0, 3.0, "oracle_file_boundary"),
            ],
        )
        trial = runner.run(fixture, phase="measured", trial_index=0, repeat_index=0)

        endpoints = [event for event in trial["events"] if event["kind"] == "endpoint"]
        self.assertEqual(len(endpoints), 3)
        self.assertEqual([event["endpoint"]["segment_index"] for event in endpoints], [0, 1, 2])
        self.assertEqual([engine.calls[i]["samples"] for i in range(3)], [16000, 16000, 16000])
        self.assertEqual([call["now"] for call in engine.calls], [1.0, 2.0, 3.0])
        self.assertEqual(trial["texts"]["final_raw"], "one two three")
        self.assertEqual(trial["timings"]["simulated"]["first_partial_ms"], None)
        self.assertIn("endpoint", trial["timings"]["simulated"]["first_partial_status"])
        self.assertEqual(trial["timings"]["simulated"]["final_after_audio_end_ms"], 250.0)


class NativeStreamArmTests(unittest.TestCase):
    def test_slow_feed_coalesces_display_ticks_but_never_drops_audio(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(
            clock,
            feed_s=1.8,
            commits=["hello", "hello world"],
            finals=[None, "hello world"],
        )
        config = hybrid_config(arm="native-stream", feed_chunk_ms=1000)
        runner = run.ReplayRunner(engine, clock, config)
        fixture = make_fixture(2.5)
        trial = runner.run(fixture, phase="measured", trial_index=0, repeat_index=0)

        self.assertEqual(len(engine.start_calls), 1)
        start = engine.start_calls[0]
        self.assertEqual(start["feed_chunk_ms"], 1000)
        self.assertEqual(start["att_context_right_frames"], 3)
        self.assertEqual(start["commit_policy"], "stable-prefix")

        events = trial["events"]
        self.assertEqual([event["kind"] for event in events], ["feed", "final"])
        self.assertEqual(events[0]["chunk_samples"], 16000)
        self.assertEqual(events[1]["chunk_samples"], 24000)
        self.assertEqual(events[1]["coalesced_ticks"], [2])
        self.assertEqual(events[1]["timing"]["frozen_prefix_samples"], 40000)

        self.assertEqual(engine.history[0], list(fixture.samples))
        self.assertEqual(len(engine.history[0]), 40000)
        for event in events:
            self.assertLessEqual(event["timing"]["frozen_prefix_samples"], event["timing"]["arrived_samples"])

        self.assertEqual(trial["texts"]["final_raw"], "hello world")
        self.assertEqual(trial["texts"]["stable_raw"], "hello world")
        self.assertIsNone(trial["final_correction"])
        self.assertEqual(trial["timings"]["simulated"]["first_partial_ms"], 2800.0)
        self.assertEqual(trial["timings"]["simulated"]["first_stable_ms"], 2800.0)
        self.assertEqual(trial["timings"]["simulated"]["final_after_audio_end_ms"], 2100.0)

    def test_stream_state_resets_between_trials(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(
            clock,
            feed_s=0.3,
            commits=["alpha", "alpha beta", "alpha beta"],
            finals=[None, None, "alpha beta"],
        )
        config = hybrid_config(arm="native-stream", feed_chunk_ms=1000)
        runner = run.ReplayRunner(engine, clock, config)
        fixture = make_fixture(2.5)

        first = runner.run(fixture, phase="measured", trial_index=0, repeat_index=0)
        second = runner.run(fixture, phase="measured", trial_index=1, repeat_index=0)

        self.assertEqual(len(engine.start_calls), 2)
        self.assertEqual(len(engine.feed_calls_history), 2)
        self.assertEqual(len(engine.history), 2)
        self.assertEqual(engine.history[0], list(fixture.samples))
        self.assertEqual(engine.history[1], list(fixture.samples))
        self.assertEqual(first["texts"]["final_raw"], "alpha beta")
        self.assertEqual(second["texts"]["final_raw"], "alpha beta")
        self.assertEqual(sum(call["samples"] for call in engine.feed_calls_history[0]), 40000)
        self.assertEqual(sum(call["samples"] for call in engine.feed_calls_history[1]), 40000)

    def test_native_conflict_and_final_correction_are_explicit(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(
            clock,
            feed_s=0.0,
            commits=["alpha beta", "alpha beta", "alpha gamma"],
            finals=[None, None, "goodbye"],
        )
        runner = run.ReplayRunner(engine, clock, hybrid_config(arm="native-stream", feed_chunk_ms=1000))
        trial = runner.run(make_fixture(2.5), phase="measured", trial_index=0, repeat_index=0)

        self.assertEqual(trial["texts"]["stable_raw"], "alpha beta")
        self.assertIsNotNone(trial["final_correction"])
        self.assertEqual(trial["final_correction"]["final_text"], "goodbye")
        self.assertGreaterEqual(len(trial["conflicts"]), 1)

    def test_native_error_marks_stream_state_fatal(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(clock, fail_on_call=0)
        runner = run.ReplayRunner(engine, clock, hybrid_config(arm="native-stream", feed_chunk_ms=1000))
        trial = runner.run(make_fixture(1.0), phase="measured", trial_index=0, repeat_index=0)
        self.assertEqual(trial["status"], "error")
        self.assertTrue(trial["fatal_stream_state"])
        self.assertIsNone(trial["wer"])


class ContextMetadataTests(unittest.TestCase):
    def test_native_default_is_r3_and_context_is_settings_derived(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(clock, feed_s=0.0, commits=["hola"], finals=["hola"])
        runner = run.ReplayRunner(
            engine, clock, hybrid_config(arm="native-stream", feed_chunk_ms=1000)
        )
        trial = runner.run(make_fixture(1.0), phase="measured", trial_index=0, repeat_index=0)

        self.assertEqual(engine.start_calls[0]["att_context_right_frames"], 3)
        context = trial["replay"]["context"]
        self.assertEqual(context["context_label"], "native_R=3")
        self.assertEqual(context["requested_att_context_right_frames"], 3)
        self.assertEqual(context["native_default_att_context_right_frames"], 3)
        self.assertEqual(context["documented_offline_batch_right_context_frames"], 13)
        self.assertIn("native_stream", context["stream_latency_setting"])
        self.assertIn("R=3", context["context_confound"])
        self.assertIn("R=13", context["context_confound"])

        exposed = trial["engine"]["native_stream"]["exposed"]
        self.assertEqual(exposed["requested"], 3)
        self.assertEqual(exposed["applied"], 3)
        self.assertIs(exposed["applied_equals_requested"], True)
        self.assertIs(exposed["engine_requested_matches_runner_request"], True)
        self.assertIsNone(exposed["accepted"])
        self.assertEqual(exposed["applied_context_status"], "engine_reported")
        self.assertEqual(exposed["applied_context_source"], "native")
        self.assertEqual(exposed["att_context_reason"], "applied_native_begin_accepted")
        self.assertEqual(exposed["adapter_default"], 3)
        self.assertIs(exposed["adapter_default_is_model_default"], False)
        self.assertEqual(exposed["documented_model_default"], 13)
        self.assertIsNone(exposed["exposed_model_default"])

    def test_native_r13_is_labelled_explicit_control_not_default(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(clock, feed_s=0.0, commits=["hola"], finals=["hola"])
        runner = run.ReplayRunner(
            engine,
            clock,
            hybrid_config(
                arm="native-stream",
                feed_chunk_ms=1000,
                right_context_frames=13,
            ),
        )
        trial = runner.run(make_fixture(1.0), phase="measured", trial_index=0, repeat_index=0)
        self.assertEqual(engine.start_calls[0]["att_context_right_frames"], 13)
        context = trial["replay"]["context"]
        self.assertEqual(context["context_label"], "native_R=13_explicit_control")
        self.assertIn("explicit", context["context_confound"].lower())
        self.assertIn("not the specified native R=3", context["limitation"])
        exposed = trial["engine"]["native_stream"]["exposed"]
        self.assertEqual(exposed["requested"], 13)
        self.assertEqual(
            exposed["applied"],
            3,
            "applied comes from engine evidence, not the request",
        )
        self.assertIs(exposed["applied_equals_requested"], False)
        self.assertIsNone(exposed["accepted"])
        self.assertEqual(exposed["applied_context_status"], "engine_reported")

    def test_native_context_unavailable_is_not_inferred_from_request(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(
            clock,
            feed_s=0.0,
            commits=["hola"],
            finals=["hola"],
            info_override={
                "capabilities": {"native_stream": True},
                "native_stream": {
                    "att_context_right_frames_default": 3,
                    "att_context_right_frames_requested": -1,
                    "att_context_right_frames_applied": None,
                    "att_context_right_frames_accepted": None,
                    "model_default_att_context_right_frames": None,
                    "applied_context_source": "unavailable",
                    "att_context_reason": "model_default_requested_not_exposed",
                },
                "stream_contract": {
                    "att_context_right_frames_default": 3,
                    "att_context_right_frames_default_is_model_default": False,
                },
            },
        )
        runner = run.ReplayRunner(
            engine, clock, hybrid_config(arm="native-stream", feed_chunk_ms=1000)
        )
        trial = runner.run(make_fixture(1.0), phase="measured", trial_index=0, repeat_index=0)
        exposed = trial["engine"]["native_stream"]["exposed"]
        self.assertEqual(exposed["requested"], 3)
        self.assertIsNone(exposed["applied"])
        self.assertIsNone(exposed["applied_equals_requested"])
        self.assertIsNone(exposed["accepted"])
        self.assertEqual(exposed["adapter_default"], 3)
        self.assertIs(exposed["adapter_default_is_model_default"], False)
        self.assertEqual(exposed["applied_context_status"], "unavailable_not_inferred")
        self.assertEqual(exposed["applied_context_source"], "unavailable")
        self.assertEqual(exposed["att_context_reason"], "model_default_requested_not_exposed")
        self.assertIn("never treated as applied", exposed["note"])

    def test_batch_arm_context_is_documented_offline_r13(self) -> None:
        context = run.context_metadata("endpoint", 3)
        self.assertEqual(context["context_label"], "offline_batch_R=13")
        self.assertIsNone(context["requested_att_context_right_frames"])
        self.assertIn("offline", context["stream_latency_setting"].lower())
        self.assertIn("not native", context["stream_latency_setting"].lower())

    def test_build_document_appends_context_limitation(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(clock, decode_s=0.0)
        runner = run.ReplayRunner(engine, clock, hybrid_config())
        trial = runner.run(make_fixture(1.0), phase="measured", trial_index=0, repeat_index=0)
        context = run.context_metadata("native-stream", 3)
        metadata = run.RunMetadata(
            arm="native-stream",
            clock_mode="fake",
            replay={"mode": "simulated_fake_clock", "context": context},
            model={"basename": "model.gguf", "sha256": "a" * 64},
            library=None,
            engine={"info": None},
            build=None,
            load={"constructor_wall_ms": None},
            invocation={"argv": [], "effective": {}},
            host={"platform": "test-only"},
            git={"commit": None},
            sources={},
            generated_at_utc="2026-01-01T00:00:00Z",
        )
        document = run.build_results_document(metadata, [trial])
        self.assertTrue(
            any("native R=3" in limitation for limitation in document["limitations"])
        )
        self.assertTrue(
            any("R=13" in limitation for limitation in document["limitations"])
        )

    def test_execute_plan_skips_later_trials_after_fatal_native_error(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(clock, fail_on_call=0)
        runner = run.ReplayRunner(
            engine, clock, hybrid_config(arm="native-stream", feed_chunk_ms=1000)
        )
        fixtures = [
            make_fixture(1.0, fixture_id="native-a"),
            make_fixture(1.0, fixture_id="native-b"),
        ]
        manifest = run.Manifest(
            schema_version=1,
            sample_rate=16000,
            path=Path("manifest.json"),
            spike_root=Path("."),
            fixtures=fixtures,
            sha256="a" * 64,
        )
        trials = run.execute_plan(manifest, runner, repeats=2, warmup=0)
        self.assertEqual(len(trials), 4)
        self.assertEqual(trials[0]["status"], "error")
        self.assertTrue(trials[0]["fatal_stream_state"])
        for trial in trials[1:]:
            self.assertEqual(trial["status"], "skipped")
            self.assertIn("poisoned", trial["error"]["message"])
            self.assertIsNone(trial["timings"])
        self.assertEqual(len({trial["trial_id"] for trial in trials}), 4)

    def test_empty_final_native_flush_is_explicit(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeStreamEngine(clock, feed_s=0.0)
        runner = run.ReplayRunner(
            engine, clock, hybrid_config(arm="native-stream", feed_chunk_ms=1000)
        )
        engine.start_stream(feed_chunk_ms=1000, att_context_right_frames=3)
        result = runner._feed_native_final(array.array("d"))
        self.assertEqual(engine.feed_calls[-1]["samples"], 0)
        self.assertTrue(engine.feed_calls[-1]["final"])
        self.assertIsInstance(result, dict)


# ---------------------------------------------------------------------------
# Manifest validation
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_wav(path: Path, seconds: float, sample_rate: int = 16000) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(round(seconds * sample_rate))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frames)
    return frames


def make_entry(tmp: Path, fixture_id: str = "tiny", seconds: float = 1.0, **overrides) -> dict:
    wav_rel = f"fixtures/{fixture_id}.wav"
    ref_rel = f"fixtures/{fixture_id}.txt"
    _write_wav(tmp / wav_rel, seconds)
    (tmp / ref_rel).write_text("alpha beta\n", encoding="utf-8")
    wav_hash = _sha256(tmp / wav_rel)
    ref_hash = _sha256(tmp / ref_rel)
    entry = {
        "id": fixture_id,
        "language": "en",
        "asr_language": "en-US",
        "wav": wav_rel,
        "reference": ref_rel,
        "wav_sha256": wav_hash,
        "reference_sha256": ref_hash,
        "duration_s": seconds,
        "source": {
            "url": "https://example.org/public-data",
            "revision": "70bb2e84b976b7e960aa89f1c648e09c59f894dd",
            "license": "CC-BY-4.0",
            "config": "en_us",
            "locale": "en_us",
            "split": "test",
            "row": 0,
            "item_id": f"{fixture_id}.wav",
            "audio_sha256": wav_hash,
            "reference_column": "raw_transcription",
        },
        "conversion": {"tool": "none"},
        "segments": [{"start_s": 0.0, "end_s": seconds, "kind": "oracle_file_boundary"}],
    }
    entry.update(overrides)
    return entry


def write_manifest(
    tmp: Path,
    entries: list[dict],
    *,
    schema_version: int = 1,
    sample_rate: int = 16000,
) -> Path:
    path = tmp / "manifest.json"
    path.write_text(
        json.dumps(
            {"schema_version": schema_version, "sample_rate": sample_rate, "fixtures": entries},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = None
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def load(self, path: Path, **kwargs):
        return run.load_manifest(path, spike_root=self.tmp, **kwargs)

    def test_valid_manifest_loads_and_verifies_files(self) -> None:
        entry = make_entry(self.tmp)
        manifest = self.load(write_manifest(self.tmp, [entry]))
        self.assertEqual(len(manifest.fixtures), 1)
        fixture = manifest.fixtures[0]
        self.assertEqual(fixture.id, "tiny")
        self.assertEqual(fixture.duration_s, 1.0)
        self.assertEqual(len(fixture.samples), 16000)
        self.assertAlmostEqual(fixture.samples[0], 0.0)
        self.assertEqual(fixture.reference_text, "alpha beta\n")
        self.assertEqual(fixture.wav_sha256, entry["wav_sha256"])
        self.assertEqual(fixture.source["revision"], "70bb2e84b976b7e960aa89f1c648e09c59f894dd")
        self.assertEqual(manifest.sample_rate, 16000)
        self.assertEqual(len(manifest.sha256), 64)

    def test_rejects_schema_version_and_sample_rate(self) -> None:
        entry = make_entry(self.tmp)
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [entry], schema_version=2))
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [entry], sample_rate=8000))

    def test_rejects_empty_fixtures_and_bad_json(self) -> None:
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, []))
        bad = self.tmp / "bad.json"
        bad.write_text("{", encoding="utf-8")
        with self.assertRaises(run.ManifestError):
            self.load(bad)

    def test_rejects_duplicate_ids_and_paths(self) -> None:
        first = make_entry(self.tmp, "one")
        second = make_entry(self.tmp, "two")
        second["id"] = "one"
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [first, second]))

        third = make_entry(self.tmp, "three")
        third["wav"] = first["wav"]
        third["wav_sha256"] = first["wav_sha256"]
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [first, third]))

    def test_rejects_traversal_absolute_and_escaping_symlink(self) -> None:
        entry = make_entry(self.tmp)
        entry["wav"] = "../outside.wav"
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [entry]))

        entry = make_entry(self.tmp)
        entry["wav"] = str((self.tmp / "fixtures" / "tiny.wav").resolve())
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [entry]))

        outside = self.tmp.parent / "outside-target.wav"
        _write_wav(outside, 1.0)
        link = self.tmp / "fixtures" / "link.wav"
        os.symlink(outside, link)
        entry = make_entry(self.tmp, "sym")
        entry["wav"] = "fixtures/link.wav"
        entry["wav_sha256"] = _sha256(outside)
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [entry]))

    def test_rejects_hash_mismatch(self) -> None:
        entry = make_entry(self.tmp)
        path = write_manifest(self.tmp, [entry])
        (self.tmp / entry["reference"]).write_text("tampered\n", encoding="utf-8")
        with self.assertRaises(run.ManifestError):
            self.load(path)

    def test_rejects_missing_files(self) -> None:
        entry = make_entry(self.tmp)
        path = write_manifest(self.tmp, [entry])
        (self.tmp / entry["reference"]).unlink()
        with self.assertRaises(run.ManifestError):
            self.load(path)

    def test_rejects_duration_mismatch(self) -> None:
        entry = make_entry(self.tmp, seconds=1.0)
        entry["duration_s"] = 1.5
        entry["segments"] = [{"start_s": 0.0, "end_s": 1.5, "kind": "oracle_file_boundary"}]
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [entry]))

    def test_rejects_bad_segment_coverage(self) -> None:
        cases = [
            [{"start_s": 0.0, "end_s": 0.4, "kind": "oracle_file_boundary"}, {"start_s": 0.5, "end_s": 1.0, "kind": "oracle_file_boundary"}],
            [{"start_s": 0.0, "end_s": 0.6, "kind": "oracle_file_boundary"}, {"start_s": 0.5, "end_s": 1.0, "kind": "oracle_file_boundary"}],
            [{"start_s": 0.0, "end_s": 0.9, "kind": "oracle_file_boundary"}],
            [{"start_s": 0.1, "end_s": 1.0, "kind": "oracle_file_boundary"}],
            [{"start_s": 0.0, "end_s": 1.0, "kind": "tested_vad"}],
            [],
        ]
        for segments in cases:
            with self.subTest(segments=segments):
                entry = make_entry(self.tmp)
                entry["segments"] = segments
                with self.assertRaises(run.ManifestError):
                    self.load(write_manifest(self.tmp, [entry]))

    def test_rejects_invalid_utf8_reference(self) -> None:
        entry = make_entry(self.tmp)
        ref_path = self.tmp / entry["reference"]
        ref_path.write_bytes(b"\xff\xfe\x00")
        entry["reference_sha256"] = _sha256(ref_path)
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [entry]))

    def test_rejects_unknown_or_empty_fixture_filter(self) -> None:
        entry = make_entry(self.tmp)
        path = write_manifest(self.tmp, [entry])
        with self.assertRaises(run.ManifestError):
            self.load(path, only_ids=["missing"])
        with self.assertRaises(run.ManifestError):
            self.load(path, only_ids=[])

    def test_selected_fixture_over_configured_max_window_is_rejected(self) -> None:
        short = make_entry(self.tmp, "short", 1.0)
        medium = make_entry(self.tmp, "medium", 2.0)
        path = write_manifest(self.tmp, [short, medium])

        manifest = self.load(path, max_window_ms=1500, only_ids=["short"])
        self.assertEqual([f.id for f in manifest.fixtures], ["short"])
        with self.assertRaises(run.UnsupportedWindowError):
            self.load(path, max_window_ms=1500, only_ids=["medium"])

        with self.assertRaises(run.UnsupportedWindowError):
            self.load(path, max_window_ms=500)

    def test_rejects_unsafe_fixture_id(self) -> None:
        entry = make_entry(self.tmp)
        entry["id"] = "../escape"
        with self.assertRaises(run.ManifestError):
            self.load(write_manifest(self.tmp, [entry]))

    def test_mixed_language_and_auto_hint_are_accepted(self) -> None:
        entry = make_entry(self.tmp, "mixed-en-es", 1.0)
        entry["language"] = "mixed"
        entry["asr_language"] = "auto"
        entry["conversion"] = {"tool": "test assembly v1"}
        entry["segments"] = [
            {"start_s": 0.0, "end_s": 0.5, "kind": "derived_assembly"},
            {"start_s": 0.5, "end_s": 1.0, "kind": "derived_assembly"},
        ]
        manifest = self.load(write_manifest(self.tmp, [entry]))
        self.assertEqual(manifest.fixtures[0].language, "mixed")
        self.assertEqual(manifest.fixtures[0].asr_language, "auto")


# ---------------------------------------------------------------------------
# Results document, sanitization and atomic output
# ---------------------------------------------------------------------------


class ResultsIntegrityTests(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_atomic_write_collision_and_overwrite(self) -> None:
        output = self.tmp / "nested" / "results.json"
        first = {"schema_version": 1, "text": "ñandú"}
        run.write_results_atomic(output, first)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), first)
        with self.assertRaises(run.OutputCollisionError):
            run.write_results_atomic(output, {"schema_version": 1, "text": "other"})
        second = {"schema_version": 1, "text": "other"}
        run.write_results_atomic(output, second, allow_overwrite=True)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8")), second)
        self.assertEqual(list(output.parent.glob("*.tmp")), [])

    def test_strict_json_rejects_nonfinite_values(self) -> None:
        output = self.tmp / "nan.json"
        with self.assertRaises(ValueError):
            run.write_results_atomic(output, {"value": float("nan")})
        self.assertFalse(output.exists())
        self.assertEqual(list(self.tmp.glob("*.tmp")), [])

    def test_sanitize_metadata_redacts_home_and_nonfinite(self) -> None:
        home = str(Path.home())
        clean = run.sanitize_metadata(
            {
                "model_path": f"{home}/.cache/models/model.gguf",
                "note": f"loaded from {home}/src",
                "nan": float("nan"),
                "infinity": float("inf"),
                "system_path": "/opt/vendor/lib.dylib",
                "nested": [float("nan"), {"library_path": "/opt/vendor/lib.dylib"}],
            }
        )
        serialized = json.dumps(clean, allow_nan=False)
        self.assertNotIn(home, serialized)
        self.assertEqual(clean["model_path"], "model.gguf")
        self.assertIsNone(clean["nan"])
        self.assertIsNone(clean["infinity"])
        self.assertEqual(clean["system_path"], "/opt/vendor/lib.dylib")
        self.assertIsNone(clean["nested"][0])
        self.assertEqual(clean["nested"][1]["library_path"], "/opt/vendor/lib.dylib")

    def test_build_results_document_metadata_aggregates_and_privacy(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(clock, decode_s=0.1, text_fn=lambda n, i: "alpha beta")
        runner = run.ReplayRunner(engine, clock, hybrid_config())
        fixture = make_fixture(2.0)
        warmup = runner.run(fixture, phase="warmup", trial_index=0, repeat_index=0)
        measured = runner.run(fixture, phase="measured", trial_index=1, repeat_index=0)

        metadata = run.RunMetadata(
            arm="hybrid",
            clock_mode="fake",
            replay={"mode": "simulated_fake_clock", "partial_interval_ms": 1000},
            model={"basename": "model.gguf", "sha256": "a" * 64, "size_bytes": 10, "path": None},
            library=None,
            engine={"info": {"temperature": float("nan")}},
            load={"constructor_wall_ms": None, "engine_reported_load_ms": None},
            invocation={"argv": [], "effective": {"arm": "hybrid"}},
            host={"platform": "test-only"},
            git={"commit": "deadbeef", "dirty": None},
            sources={"run.py": "b" * 64, "policy.py": "c" * 64, "metrics.py": "d" * 64},
            generated_at_utc="2026-01-01T00:00:00Z",
        )
        document = run.build_results_document(metadata, [warmup, measured])

        self.assertEqual(document["schema_version"], 1)
        self.assertEqual(document["clock_mode"], "fake")
        self.assertEqual(document["generated_at_utc"], "2026-01-01T00:00:00Z")
        self.assertEqual(len(document["trials"]), 2)
        self.assertEqual(len({trial["trial_id"] for trial in document["trials"]}), 2)
        self.assertEqual(document["aggregates"]["measured_trials"], 1)
        self.assertEqual(document["aggregates"]["warmup_trials"], 1)
        self.assertEqual(document["aggregates"]["ok_trials"], 1)
        self.assertEqual(document["aggregates"]["wer"]["reference_tokens"], 2)
        self.assertEqual(document["aggregates"]["wer"]["errors"], 0)
        self.assertEqual(document["fixtures"][0]["wav"]["relative"], "fixtures/tiny.wav")
        self.assertEqual(document["fixtures"][0]["source"]["revision"], "70bb2e84b976b7e960aa89f1c648e09c59f894dd")
        self.assertIsNone(document["engine"]["info"]["temperature"])
        self.assertIn("word_end_latency", document["metric_definitions"]["unsupported"])
        self.assertIsNone(measured["timings"]["measured"])
        self.assertIsNotNone(measured["timings"]["simulated"])

        serialized = json.dumps(document, allow_nan=False, ensure_ascii=False)
        self.assertNotIn(str(Path.home()), serialized)

    def test_capability_flags_are_enforced_only_when_reported(self) -> None:
        run.check_arm_capabilities({"capabilities": {"native_stream": True}}, "native-stream")
        run.check_arm_capabilities({"capabilities": {"batch": True}}, "hybrid")
        run.check_arm_capabilities(None, "hybrid")
        with self.assertRaises(run.CapabilityError):
            run.check_arm_capabilities({"capabilities": {"native_stream": False}}, "native-stream")
        with self.assertRaises(run.CapabilityError):
            run.check_arm_capabilities({"capabilities": {"batch": False}}, "endpoint")

    def test_runner_sanitizes_nonfinite_token_times(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(
            clock,
            decode_s=0.0,
            tokens=[{"text": "alpha", "start_ms": 0.0, "end_ms": float("nan")}],
        )
        runner = run.ReplayRunner(engine, clock, hybrid_config())
        trial = runner.run(make_fixture(1.0), phase="measured", trial_index=0, repeat_index=0)
        self.assertIsNone(trial["events"][0]["tokens"][0]["end_ms"])
        json.dumps(trial, allow_nan=False)

    def test_native_extra_is_retained_and_nonfinite_metadata_sanitized(self) -> None:
        clock = run.FakeClock(0.0)
        engine = FakeBatchEngine(
            clock,
            decode_s=0.0,
            hints={"revisions": [{"index": 0}], "commit_ms": float("inf")},
        )
        runner = run.ReplayRunner(engine, clock, hybrid_config())
        trial = runner.run(make_fixture(1.0), phase="measured", trial_index=0, repeat_index=0)
        extra = trial["events"][0]["native_extra"]
        self.assertEqual(extra["revisions"], [{"index": 0}])
        self.assertIsNone(extra["commit_ms"])
        json.dumps(trial, allow_nan=False)

    def test_collect_sources_includes_executed_runner_modules(self) -> None:
        sources = run.collect_sources()
        for name in ("run.py", "policy.py", "metrics.py", "fixtures/manifest_tools.py"):
            with self.subTest(name=name):
                self.assertIn(name, sources)
                self.assertRegex(sources[name]["sha256"], r"^[0-9a-f]{64}$")

    def test_collect_build_metadata_includes_lock_and_artifact_identity(self) -> None:
        build = run.collect_build_metadata()
        self.assertTrue(build["available"])
        self.assertRegex(build["lock_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(build["artifact_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(build["engine"]["name"], "transcribe.cpp")

    def test_cli_parser_documents_required_settings(self) -> None:
        parser = run.build_parser()
        destinations = {action.dest for action in parser._actions}
        required = {
            "model",
            "library",
            "manifest",
            "arm",
            "output",
            "repeats",
            "warmup",
            "fixture",
            "language",
            "asr_language",
            "partial_interval_ms",
            "max_window_ms",
            "feed_chunk_ms",
            "right_context_frames",
            "commit_policy",
            "agreement_n",
            "clock_mode",
            "window_mode",
            "threads",
            "cpu",
            "allow_overwrite",
        }
        self.assertTrue(required.issubset(destinations), required - destinations)
        args = parser.parse_args(["--model", "model.gguf", "--arm", "native-stream", "--output", "out.json"])
        self.assertEqual(args.right_context_frames, 3)
        self.assertEqual(args.clock_mode, "real")
        self.assertEqual(args.window_mode, "fixed-start")


if __name__ == "__main__":
    unittest.main()
