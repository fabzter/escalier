"""Deterministic tests for WER normalization/accounting and replay timing metrics."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SPIKE_ROOT = Path(__file__).resolve().parents[1]
if str(SPIKE_ROOT) not in sys.path:
    sys.path.insert(0, str(SPIKE_ROOT))

import metrics  # noqa: E402


class NormalizationTests(unittest.TestCase):
    def test_wer_normalizer_v1(self) -> None:
        self.assertEqual(metrics.normalize_text("  ¡Hola,   MÉXICO!\n"), "hola méxico")
        self.assertEqual(metrics.normalize_text("niño NINO"), "niño nino")
        self.assertEqual(metrics.normalize_text("3.14"), "3 14")
        self.assertEqual(metrics.normalize_text("¿Qué?"), "qué")
        self.assertEqual(metrics.normalize_text(""), "")
        self.assertEqual(metrics.normalize_text(" \t\n "), "")

    def test_nfc_combining_marks(self) -> None:
        self.assertEqual(metrics.normalize_text("me\u0301xico"), "méxico")

    def test_digits_are_not_expanded(self) -> None:
        self.assertEqual(metrics.normalize_text("1,000"), "1 000")
        self.assertEqual(metrics.normalize_text("veintiuno 21"), "veintiuno 21")

    def test_normalized_tokens(self) -> None:
        self.assertEqual(metrics.normalize_tokens("Hello, world!"), ["hello", "world"])
        self.assertEqual(metrics.normalize_tokens(""), [])


class WerTests(unittest.TestCase):
    def test_substitution_and_insertion_accounting(self) -> None:
        result = metrics.wer("a b c", "a x c d")
        self.assertEqual(result["reference_tokens"], 3)
        self.assertEqual(result["hypothesis_tokens"], 4)
        self.assertEqual(result["substitutions"], 1)
        self.assertEqual(result["deletions"], 0)
        self.assertEqual(result["insertions"], 1)
        self.assertEqual(result["errors"], 2)
        self.assertAlmostEqual(result["wer"], 2 / 3)
        self.assertEqual(result["reference_normalized"], "a b c")
        self.assertEqual(result["hypothesis_normalized"], "a x c d")

    def test_deletion_accounting(self) -> None:
        result = metrics.wer("a b c", "a c")
        self.assertEqual((result["substitutions"], result["deletions"], result["insertions"]), (0, 1, 0))
        self.assertAlmostEqual(result["wer"], 1 / 3)

    def test_normalization_before_scoring(self) -> None:
        result = metrics.wer("Hello, world!", "hello world")
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["wer"], 0.0)
        result = metrics.wer("3.14", "3 14")
        self.assertEqual(result["errors"], 0)

    def test_accents_are_scored(self) -> None:
        result = metrics.wer("MÉXICO", "mexico")
        self.assertEqual(result["substitutions"], 1)
        self.assertEqual(result["wer"], 1.0)

    def test_empty_reference_has_null_wer_but_preserves_counts(self) -> None:
        result = metrics.wer("", "a b")
        self.assertIsNone(result["wer"])
        self.assertEqual(result["reference_tokens"], 0)
        self.assertEqual(result["insertions"], 2)
        self.assertEqual(result["errors"], 2)

    def test_both_empty(self) -> None:
        result = metrics.wer("", "   ")
        self.assertIsNone(result["wer"])
        self.assertEqual(result["errors"], 0)

    def test_empty_hypothesis_is_all_deletions(self) -> None:
        result = metrics.wer("a b", "")
        self.assertEqual(result["deletions"], 2)
        self.assertEqual(result["wer"], 1.0)

    def test_deterministic_tie_break_prefers_substitution(self) -> None:
        result = metrics.wer("a b", "b a")
        self.assertEqual(result["substitutions"], 2)
        self.assertEqual(result["deletions"], 0)
        self.assertEqual(result["insertions"], 0)
        self.assertEqual(result["wer"], 1.0)

    def test_operation_alignment_is_retained(self) -> None:
        result = metrics.wer("a b c", "a x c d")
        ops = [(op["op"], op["reference"], op["hypothesis"]) for op in result["operations"]]
        self.assertEqual(
            ops,
            [
                ("match", "a", "a"),
                ("substitution", "b", "x"),
                ("match", "c", "c"),
                ("insertion", None, "d"),
            ],
        )

    def test_micro_aggregate_counts_not_mean_ratios(self) -> None:
        results = [
            metrics.wer("a b", "a x"),  # 1 error / 2 refs
            metrics.wer("", "z"),  # 1 insertion / 0 refs, null ratio
            metrics.wer("a", ""),  # 1 deletion / 1 ref
        ]
        aggregate = metrics.micro_aggregate(results)
        self.assertEqual(aggregate["reference_tokens"], 3)
        self.assertEqual(aggregate["substitutions"], 1)
        self.assertEqual(aggregate["deletions"], 1)
        self.assertEqual(aggregate["insertions"], 1)
        self.assertEqual(aggregate["errors"], 3)
        self.assertEqual(aggregate["micro_wer"], 1.0)
        self.assertEqual(aggregate["trials"], 3)
        self.assertEqual(aggregate["trials_with_reference"], 2)
        self.assertEqual(aggregate["trials_empty_reference"], 1)
        self.assertIsNotNone(aggregate["macro_mean_wer"])

    def test_micro_aggregate_all_empty_references(self) -> None:
        aggregate = metrics.micro_aggregate([metrics.wer("", "x"), metrics.wer("", "")])
        self.assertIsNone(aggregate["micro_wer"])
        self.assertIsNone(aggregate["macro_mean_wer"])
        self.assertEqual(aggregate["errors"], 1)
        self.assertEqual(aggregate["reference_tokens"], 0)


class TimingMetricTests(unittest.TestCase):
    def _events(self) -> list[dict]:
        return [
            {
                "kind": "partial",
                "text": "",
                "native": {},
                "policy": {"stable_text": ""},
                "timing": {
                    "call_start_ms": 900.0,
                    "call_end_ms": 950.0,
                    "call_wall_ms": 50.0,
                    "queue_lag_ms": 0.0,
                    "backlog_samples": 0,
                    "backlog_samples_after": 0,
                    "frozen_prefix_samples": 14400,
                },
            },
            {
                "kind": "partial",
                "text": "alpha",
                "native": {},
                "policy": {"stable_text": ""},
                "timing": {
                    "call_start_ms": 1000.0,
                    "call_end_ms": 1200.0,
                    "call_wall_ms": 200.0,
                    "queue_lag_ms": 10.0,
                    "backlog_samples": 1600,
                    "backlog_samples_after": 3200,
                    "frozen_prefix_samples": 16000,
                },
            },
            {
                "kind": "partial",
                "text": "alpha beta",
                "native": {},
                "policy": {"stable_text": "alpha"},
                "timing": {
                    "call_start_ms": 1500.0,
                    "call_end_ms": 1700.0,
                    "call_wall_ms": 200.0,
                    "queue_lag_ms": 20.0,
                    "backlog_samples": 0,
                    "backlog_samples_after": 0,
                    "frozen_prefix_samples": 24000,
                },
            },
            {
                "kind": "final",
                "text": "alpha beta",
                "decode_ms": 12.5,
                "timing": {
                    "call_start_ms": 3000.0,
                    "call_end_ms": 3400.0,
                    "call_wall_ms": 400.0,
                    "queue_lag_ms": 0.0,
                    "backlog_samples": 0,
                    "backlog_samples_after": 0,
                    "frozen_prefix_samples": 32000,
                },
            },
        ]

    def test_fake_clock_populates_only_simulated_fields(self) -> None:
        result = metrics.compute_timings(
            self._events(), audio_end_ms=3000.0, arm="hybrid", clock_mode="fake"
        )
        self.assertIsNone(result["measured"])
        self.assertEqual(result["simulated"]["first_partial_ms"], 1200.0)
        self.assertEqual(result["simulated"]["first_stable_ms"], 1700.0)
        self.assertEqual(result["simulated"]["final_after_audio_end_ms"], 400.0)
        self.assertEqual(result["simulated"]["queue_lag_max_ms"], 20.0)
        self.assertEqual(result["simulated"]["backlog_max_samples"], 3200)
        self.assertEqual(result["simulated"]["decode_calls"], 4)
        self.assertIsNone(result["word_end_latency_ms"])
        self.assertIn("no independent gold word timings", result["word_end_latency_status"])

    def test_real_clock_populates_measured_and_not_simulated(self) -> None:
        result = metrics.compute_timings(
            self._events(), audio_end_ms=3000.0, arm="hybrid", clock_mode="real"
        )
        self.assertIsNotNone(result["measured"])
        self.assertIsNone(result["simulated"])
        self.assertEqual(result["measured"]["decode_calls"], 4)

    def test_endpoint_arm_has_no_partial_or_stable_metrics(self) -> None:
        events = [
            {
                "kind": "endpoint",
                "text": "alpha",
                "native": {},
                "policy": None,
                "timing": {
                    "call_start_ms": 1000.0,
                    "call_end_ms": 1300.0,
                    "call_wall_ms": 300.0,
                    "queue_lag_ms": 0.0,
                    "backlog_samples": 0,
                    "backlog_samples_after": 0,
                    "frozen_prefix_samples": 16000,
                },
            },
            {
                "kind": "endpoint",
                "text": "beta",
                "native": {},
                "policy": None,
                "timing": {
                    "call_start_ms": 2000.0,
                    "call_end_ms": 2300.0,
                    "call_wall_ms": 300.0,
                    "queue_lag_ms": 0.0,
                    "backlog_samples": 0,
                    "backlog_samples_after": 0,
                    "frozen_prefix_samples": 16000,
                },
            },
        ]
        result = metrics.compute_timings(events, audio_end_ms=2000.0, arm="endpoint", clock_mode="fake")
        simulated = result["simulated"]
        self.assertIsNone(simulated["first_partial_ms"])
        self.assertIn("endpoint", simulated["first_partial_status"])
        self.assertIsNone(simulated["first_stable_ms"])
        self.assertEqual(simulated["final_after_audio_end_ms"], 300.0)

    def test_native_committed_text_drives_first_stable(self) -> None:
        events = [
            {
                "kind": "feed",
                "text": "alpha",
                "native": {"committed_text": ""},
                "policy": None,
                "timing": {
                    "call_start_ms": 1000.0,
                    "call_end_ms": 1100.0,
                    "call_wall_ms": 100.0,
                    "queue_lag_ms": 0.0,
                    "backlog_samples": 0,
                    "backlog_samples_after": 0,
                    "frozen_prefix_samples": 16000,
                },
            },
            {
                "kind": "feed",
                "text": "alpha beta",
                "native": {"committed_text": "alpha"},
                "policy": None,
                "timing": {
                    "call_start_ms": 2000.0,
                    "call_end_ms": 2100.0,
                    "call_wall_ms": 100.0,
                    "queue_lag_ms": 0.0,
                    "backlog_samples": 0,
                    "backlog_samples_after": 0,
                    "frozen_prefix_samples": 32000,
                },
            },
            {
                "kind": "final",
                "text": "alpha beta",
                "native": {"committed_text": "alpha beta"},
                "timing": {
                    "call_start_ms": 3000.0,
                    "call_end_ms": 3200.0,
                    "call_wall_ms": 200.0,
                    "queue_lag_ms": 0.0,
                    "backlog_samples": 0,
                    "backlog_samples_after": 0,
                    "frozen_prefix_samples": 40000,
                },
            },
        ]
        result = metrics.compute_timings(events, audio_end_ms=3000.0, arm="native-stream", clock_mode="fake")
        simulated = result["simulated"]
        self.assertEqual(simulated["first_partial_ms"], 1100.0)
        self.assertEqual(simulated["first_stable_ms"], 2100.0)

    def test_missing_final_event_does_not_fabricate_zero(self) -> None:
        result = metrics.compute_timings([], audio_end_ms=1000.0, arm="hybrid", clock_mode="fake")
        simulated = result["simulated"]
        self.assertIsNone(simulated["final_after_audio_end_ms"])
        self.assertEqual(simulated["final_after_audio_end_status"], "no_final_event")
        self.assertIsNone(simulated["first_partial_ms"])
        self.assertEqual(simulated["decode_calls"], 0)
        self.assertIsNone(simulated["call_wall_total_ms"])


if __name__ == "__main__":
    unittest.main()
