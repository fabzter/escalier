"""Runner-side stable-prefix policies.

Two policies are deliberately distinct:

* :class:`StablePrefixPolicy` implements word-level LocalAgreement-2 for the
  hybrid growing-prefix arm.  Words are compared after Unicode NFC/casefold and
  punctuation removal; accents and ``ñ`` are preserved.  A word enters stable
  history only when it is in the common prefix of two consecutive hypotheses.
* :class:`NativeCommitTracker` tracks native ``committed_text`` for the
  genuine-streaming arm.  It compares raw whitespace-canonicalized character
  prefixes because the native policy's units are not assumed to equal runner
  words.

Both are append-only: a later disagreement never deletes confirmed history.
Conflicts and final corrections are returned as explicit records so the runner
can publish them as events alongside the raw hypothesis text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import metrics

AGREEMENT_N = 2


class PolicyError(ValueError):
    """A policy configuration or input is unsupported."""


class UnsupportedAgreementError(PolicyError):
    """Only LocalAgreement-2 is implemented by this spike."""


def fold(text: str) -> str:
    return metrics.fold(text)


def normalize_word(word: str) -> str:
    return metrics.normalize_token(word)


@dataclass(frozen=True)
class ComparableWord:
    raw: str
    normalized: str


def comparable_words(text: str) -> list[ComparableWord]:
    """Whitespace words with punctuation removed; punctuation-only words dropped."""
    if not isinstance(text, str):
        raise PolicyError("hypothesis text must be a string")
    words: list[ComparableWord] = []
    for raw in text.split():
        normalized = normalize_word(raw)
        if normalized:
            words.append(ComparableWord(raw=raw, normalized=normalized))
    return words


def common_prefix_len(left: Sequence[str], right: Sequence[str]) -> int:
    limit = min(len(left), len(right))
    index = 0
    while index < limit and left[index] == right[index]:
        index += 1
    return index


@dataclass
class PolicyUpdate:
    event_index: int
    hypothesis_text: str
    common_prefix_len: int
    agreed_prefix_len: int
    stable_len_before: int
    stable_len_after: int
    new_stable_words: list[str]
    stable_text: str
    stable_normalized: str
    tentative_text: str
    display_text: str
    conflict: dict | None

    def as_dict(self) -> dict:
        return {
            "policy": "runner_word_local_agreement_2",
            "event_index": self.event_index,
            "hypothesis_text": self.hypothesis_text,
            "common_prefix_len": self.common_prefix_len,
            "agreed_prefix_len": self.agreed_prefix_len,
            "stable_len_before": self.stable_len_before,
            "stable_len_after": self.stable_len_after,
            "new_stable_words": list(self.new_stable_words),
            "stable_text": self.stable_text,
            "stable_normalized": self.stable_normalized,
            "tentative_text": self.tentative_text,
            "display_text": self.display_text,
            "conflict": self.conflict,
        }


class StablePrefixPolicy:
    """Append-only word-level LocalAgreement-2.

    The first hypothesis establishes a comparison baseline but commits nothing.
    From the second hypothesis onward, newly agreed words are appended to
    stable history.  A hypothesis that does not begin with the confirmed stable
    words is recorded as a conflict and leaves stable history untouched.
    """

    def __init__(self, agreement_n: int = AGREEMENT_N) -> None:
        if agreement_n != AGREEMENT_N or isinstance(agreement_n, bool):
            raise UnsupportedAgreementError(
                f"only LocalAgreement-{AGREEMENT_N} is supported, got {agreement_n!r}"
            )
        self.agreement_n = agreement_n
        self._previous_normalized: list[str] = []
        self._stable_words: list[str] = []
        self._stable_normalized: list[str] = []
        self._updates = 0
        self._history: list[dict] = []
        self._conflicts: list[dict] = []

    @property
    def stable_words(self) -> list[str]:
        return list(self._stable_words)

    @property
    def stable_normalized(self) -> list[str]:
        return list(self._stable_normalized)

    @property
    def stable_text(self) -> str:
        return " ".join(self._stable_words)

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    @property
    def conflicts(self) -> list[dict]:
        return list(self._conflicts)

    def update(self, text: str, *, event_index: int) -> PolicyUpdate:
        current = comparable_words(text)
        current_normalized = [word.normalized for word in current]
        stable_len_before = len(self._stable_normalized)

        if self._updates == 0:
            common = 0
        else:
            common = common_prefix_len(self._previous_normalized, current_normalized)

        stable_matches = (
            current_normalized[:stable_len_before] == self._stable_normalized
        )
        conflict: dict | None = None
        new_words: list[str] = []

        if not stable_matches:
            conflict = {
                "type": "stable_prefix_disagreement",
                "event_index": event_index,
                "stable_text": self.stable_text,
                "stable_normalized": " ".join(self._stable_normalized),
                "hypothesis_text": text,
                "common_prefix_len": common,
                "agreed_prefix_len": common,
                "stable_len": stable_len_before,
                "note": (
                    "confirmed stable history is append-only; this conflicting "
                    "hypothesis is retained raw in the event"
                ),
            }
            self._conflicts.append(conflict)
        elif common > stable_len_before:
            for word in current[stable_len_before:common]:
                self._stable_words.append(word.raw)
                self._stable_normalized.append(word.normalized)
                new_words.append(word.raw)
                self._history.append(
                    {
                        "event_index": event_index,
                        "word": word.raw,
                        "normalized": word.normalized,
                    }
                )

        self._previous_normalized = current_normalized
        self._updates += 1
        stable_len_after = len(self._stable_normalized)

        if conflict is not None:
            tentative_text = ""
            display_text = self.stable_text
        else:
            tentative_text = " ".join(
                word.raw for word in current[stable_len_after:]
            )
            if stable_len_after == 0:
                display_text = text
            else:
                display_text = " ".join(
                    part for part in (self.stable_text, tentative_text) if part
                )

        return PolicyUpdate(
            event_index=event_index,
            hypothesis_text=text,
            common_prefix_len=common,
            agreed_prefix_len=common,
            stable_len_before=stable_len_before,
            stable_len_after=stable_len_after,
            new_stable_words=new_words,
            stable_text=self.stable_text,
            stable_normalized=" ".join(self._stable_normalized),
            tentative_text=tentative_text,
            display_text=display_text,
            conflict=conflict,
        )

    def finalize(self, text: str, *, event_index: int) -> dict:
        """Compare the authoritative final text without rewriting history."""
        final = comparable_words(text)
        final_normalized = [word.normalized for word in final]
        correction: dict | None = None
        if self._stable_normalized:
            prefix_ok = (
                final_normalized[: len(self._stable_normalized)]
                == self._stable_normalized
            )
            if not prefix_ok:
                correction = {
                    "type": "final_correction",
                    "event_index": event_index,
                    "stable_text": self.stable_text,
                    "stable_normalized": " ".join(self._stable_normalized),
                    "final_text": text,
                    "note": (
                        "final text is authoritative; confirmed stable history "
                        "is retained unchanged for audit"
                    ),
                }
        return {
            "final_text": text,
            "final_normalized": metrics.normalize_text(text),
            "stable_text": self.stable_text,
            "stable_normalized": " ".join(self._stable_normalized),
            "stable_words": list(self._stable_words),
            "final_correction": correction,
            "history": self.history,
            "conflicts": self.conflicts,
        }


def _canonical_whitespace(text: str) -> str:
    return " ".join(text.split())


class NativeCommitTracker:
    """Track native ``committed_text`` as append-only raw character prefixes."""

    def __init__(self) -> None:
        self._stable_text = ""
        self._history: list[dict] = []
        self._conflicts: list[dict] = []

    @property
    def stable_text(self) -> str:
        return self._stable_text

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    @property
    def conflicts(self) -> list[dict]:
        return list(self._conflicts)

    def update(self, text: str, *, event_index: int) -> dict:
        received = _canonical_whitespace(text if isinstance(text, str) else "")
        changed = received != self._stable_text
        conflict: dict | None = None
        if self._stable_text and not received.startswith(self._stable_text):
            conflict = {
                "type": "stable_prefix_disagreement",
                "event_index": event_index,
                "stable_text": self._stable_text,
                "received_text": received,
                "note": (
                    "native committed text is append-only in this audit; the "
                    "conflicting snapshot is retained raw in the event"
                ),
            }
            self._conflicts.append(conflict)
        elif changed and received:
            self._stable_text = received
            self._history.append(
                {"event_index": event_index, "committed_text": received}
            )
        return {
            "policy": "native_committed_text",
            "event_index": event_index,
            "changed": changed,
            "received_text": received,
            "stable_text": self._stable_text,
            "conflict": conflict,
        }

    def finalize(self, text: str, *, event_index: int) -> dict:
        final_text = text if isinstance(text, str) else ""
        canonical_final = _canonical_whitespace(final_text)
        correction: dict | None = None
        if self._stable_text and not canonical_final.startswith(self._stable_text):
            correction = {
                "type": "final_correction",
                "event_index": event_index,
                "stable_text": self._stable_text,
                "final_text": final_text,
                "note": (
                    "final_text is authoritative; native committed history is "
                    "retained unchanged for audit"
                ),
            }
        return {
            "final_text": final_text,
            "stable_text": self._stable_text,
            "final_correction": correction,
            "history": self.history,
            "conflicts": self.conflicts,
        }
