"""Deterministic tests for runner-side stable-prefix policies.

No engine, audio or filesystem fixtures are needed here.  The tests pin the
word comparison rules from SPEC.md and the append-only stable-history behaviour.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SPIKE_ROOT = Path(__file__).resolve().parents[1]
if str(SPIKE_ROOT) not in sys.path:
    sys.path.insert(0, str(SPIKE_ROOT))

import policy  # noqa: E402


class WordNormalizationTests(unittest.TestCase):
    def test_casefold_and_punctuation_ignored(self) -> None:
        words = policy.comparable_words("Hello, WORLD!")
        self.assertEqual([w.normalized for w in words], ["hello", "world"])
        self.assertEqual([w.raw for w in words], ["Hello,", "WORLD!"])

    def test_accents_and_enye_are_preserved(self) -> None:
        self.assertNotEqual(policy.normalize_word("méxico"), policy.normalize_word("mexico"))
        self.assertNotEqual(policy.normalize_word("niño"), policy.normalize_word("nino"))
        self.assertEqual(policy.normalize_word("MÉXICO"), "méxico")
        self.assertEqual(policy.normalize_word("NiÑo"), "niño")

    def test_combining_marks_are_nfc_normalized(self) -> None:
        decomposed = "me\u0301xico"
        self.assertEqual(policy.normalize_word(decomposed), policy.normalize_word("méxico"))

    def test_punctuation_only_tokens_are_ignored(self) -> None:
        words = policy.comparable_words("alpha — beta ...")
        self.assertEqual([w.normalized for w in words], ["alpha", "beta"])

    def test_common_prefix_respects_word_boundaries(self) -> None:
        self.assertEqual(policy.common_prefix_len(["a", "b"], ["a", "b", "c"]), 2)
        self.assertEqual(policy.common_prefix_len(["a", "b"], ["a", "x"]), 1)
        self.assertEqual(policy.common_prefix_len([], ["a"]), 0)


class StablePrefixPolicyTests(unittest.TestCase):
    def test_requires_two_consecutive_hypotheses(self) -> None:
        policy_ = policy.StablePrefixPolicy()
        first = policy_.update("Hello, world foo!", event_index=0)
        self.assertEqual(first.stable_text, "")
        self.assertEqual(first.new_stable_words, [])
        self.assertEqual(first.display_text, "Hello, world foo!")

        second = policy_.update("hello world bar", event_index=1)
        self.assertEqual(second.common_prefix_len, 2)
        self.assertEqual(second.new_stable_words, ["hello", "world"])
        self.assertEqual(second.stable_text, "hello world")
        self.assertEqual(policy_.stable_words, ["hello", "world"])

    def test_stable_history_is_append_only_and_disagreement_is_recorded(self) -> None:
        p = policy.StablePrefixPolicy()
        p.update("alpha beta gamma", event_index=0)
        p.update("alpha beta delta", event_index=1)
        self.assertEqual(p.stable_text, "alpha beta")

        conflict = p.update("alpha zeta", event_index=2)
        self.assertIsNotNone(conflict.conflict)
        self.assertEqual(conflict.conflict["type"], "stable_prefix_disagreement")
        self.assertEqual(conflict.conflict["stable_text"], "alpha beta")
        self.assertEqual(conflict.conflict["hypothesis_text"], "alpha zeta")
        self.assertEqual(conflict.new_stable_words, [])
        self.assertEqual(p.stable_text, "alpha beta")

        # A later re-agreement must not erase or duplicate confirmed history.
        again = p.update("alpha beta epsilon", event_index=3)
        self.assertIsNone(again.conflict)
        self.assertEqual(again.new_stable_words, [])
        self.assertEqual(again.stable_text, "alpha beta")
        self.assertEqual(again.tentative_text, "epsilon")

    def test_new_stable_words_extend_agreed_prefix(self) -> None:
        p = policy.StablePrefixPolicy()
        p.update("one two", event_index=0)
        p.update("one two three", event_index=1)
        self.assertEqual(p.stable_text, "one two")
        third = p.update("one two three four", event_index=2)
        self.assertEqual(third.common_prefix_len, 3)
        self.assertEqual(third.new_stable_words, ["three"])
        self.assertEqual(p.stable_text, "one two three")
        self.assertEqual(third.display_text, "one two three four")

    def test_punctuation_raw_words_retained_in_stable_text(self) -> None:
        p = policy.StablePrefixPolicy()
        p.update("Hello, world!", event_index=0)
        p.update("hello world again", event_index=1)
        self.assertEqual(p.stable_text, "hello world")
        self.assertEqual([h["normalized"] for h in p.history], ["hello", "world"])
        self.assertEqual([h["word"] for h in p.history], ["hello", "world"])

    def test_final_correction_is_explicit_and_history_survives(self) -> None:
        p = policy.StablePrefixPolicy()
        p.update("alpha beta", event_index=0)
        p.update("alpha beta", event_index=1)
        result = p.finalize("alpha gamma", event_index=2)
        self.assertEqual(result["final_text"], "alpha gamma")
        self.assertIsNotNone(result["final_correction"])
        self.assertEqual(result["final_correction"]["type"], "final_correction")
        self.assertEqual(result["final_correction"]["stable_text"], "alpha beta")
        self.assertEqual(result["final_correction"]["final_text"], "alpha gamma")
        self.assertEqual(p.stable_text, "alpha beta")
        self.assertEqual(len(p.history), 2)

    def test_final_prefix_extension_is_not_a_correction(self) -> None:
        p = policy.StablePrefixPolicy()
        p.update("alpha beta", event_index=0)
        p.update("alpha beta", event_index=1)
        result = p.finalize("alpha beta gamma", event_index=2)
        self.assertIsNone(result["final_correction"])

    def test_final_truncation_is_a_correction(self) -> None:
        p = policy.StablePrefixPolicy()
        p.update("alpha beta", event_index=0)
        p.update("alpha beta", event_index=1)
        result = p.finalize("alpha", event_index=2)
        self.assertIsNotNone(result["final_correction"])

    def test_unsupported_agreement_n_is_rejected(self) -> None:
        with self.assertRaises(policy.UnsupportedAgreementError):
            policy.StablePrefixPolicy(agreement_n=3)
        with self.assertRaises(policy.UnsupportedAgreementError):
            policy.StablePrefixPolicy(agreement_n=1)

    def test_empty_hypothesis_does_not_commit_stable_words(self) -> None:
        p = policy.StablePrefixPolicy()
        p.update("", event_index=0)
        second = p.update("", event_index=1)
        self.assertEqual(second.stable_text, "")
        self.assertEqual(second.new_stable_words, [])


class NativeCommitTrackerTests(unittest.TestCase):
    def test_native_committed_text_is_append_only(self) -> None:
        tracker = policy.NativeCommitTracker()
        first = tracker.update(" hello  wor ", event_index=0)
        self.assertTrue(first["changed"])
        self.assertIsNone(first["conflict"])
        self.assertEqual(first["stable_text"], "hello wor")

        second = tracker.update("hello world", event_index=1)
        self.assertTrue(second["changed"])
        self.assertIsNone(second["conflict"])
        self.assertEqual(second["stable_text"], "hello world")

        third = tracker.update("hello world", event_index=2)
        self.assertFalse(third["changed"])
        self.assertEqual(tracker.stable_text, "hello world")

    def test_native_disagreement_is_recorded_without_rewriting(self) -> None:
        tracker = policy.NativeCommitTracker()
        tracker.update("hello world", event_index=0)
        conflict = tracker.update("hello there", event_index=1)
        self.assertIsNotNone(conflict["conflict"])
        self.assertEqual(conflict["conflict"]["type"], "stable_prefix_disagreement")
        self.assertEqual(conflict["conflict"]["stable_text"], "hello world")
        self.assertEqual(tracker.stable_text, "hello world")

    def test_native_rewind_to_empty_is_recorded_as_conflict(self) -> None:
        tracker = policy.NativeCommitTracker()
        tracker.update("hello world", event_index=0)
        rewind = tracker.update("", event_index=1)
        self.assertIsNotNone(rewind["conflict"])
        self.assertEqual(rewind["conflict"]["type"], "stable_prefix_disagreement")
        self.assertEqual(tracker.stable_text, "hello world")

    def test_native_final_correction(self) -> None:
        tracker = policy.NativeCommitTracker()
        tracker.update("hello world", event_index=0)
        correction = tracker.finalize("hello there", event_index=1)
        self.assertIsNotNone(correction["final_correction"])
        self.assertEqual(correction["final_correction"]["stable_text"], "hello world")
        self.assertEqual(tracker.stable_text, "hello world")

    def test_native_final_extension_is_not_a_correction(self) -> None:
        tracker = policy.NativeCommitTracker()
        tracker.update("hello", event_index=0)
        correction = tracker.finalize("hello world", event_index=1)
        self.assertIsNone(correction["final_correction"])


if __name__ == "__main__":
    unittest.main()
