"""Metric and normalization helpers for the transcription replay runner.

This module is deliberately standard-library only and free of engine imports so
the deterministic test suite runs without a native helper or model.

Definitions (also published in the result document):

* Normalizer v1: Unicode NFC, ``str.casefold()``, every Unicode punctuation
  character (general category ``P*``) replaced by a space, whitespace collapsed
  and trimmed.  Accents and ``ñ`` are preserved; digits are unchanged and no
  number expansion is attempted.  This is not any vendor's WER normalizer.
* WER: ``(S + D + I) / reference_token_count``.  An empty reference has null
  WER with its S/D/I counts preserved.  Alignment is deterministic Levenshtein;
  cost ties prefer match, then substitution, then deletion, then insertion.
* ``first_partial_ms`` / ``first_stable_ms`` are result arrival times (the
  runner's call return) relative to replay start ``t0``.  ``t0`` is defined one
  sample period before the first fixture sample becomes available (the arrival
  model makes sample i available at ``t0 + (i+1)/sample_rate``).  These fields
  are therefore conservatively high by one sample period (0.0625 ms at
  16 kHz) versus a literal first-sample-availability origin.  The convention
  is retained for metric stability and recorded in the result definitions.
* ``final_after_audio_end_ms`` is the final call return minus the fixture
  audio-end arrival.
* ``call_wall_ms`` is runner monotonic elapsed around one engine call and
  includes validation/transport/native compute; it is not pure GPU decode time.
* ``word_end_latency_ms`` is unsupported/null: there are no independent gold
  word timings, and model token end times are hypotheses rather than truth.
"""

from __future__ import annotations

import math
import unicodedata
from typing import Any, Iterable, Sequence

WORD_END_LATENCY_STATUS = (
    "unsupported: no independent gold word timings exist; native token end_ms "
    "values are model hypotheses, not verified ground truth, so word-end/"
    "display latency is not reported"
)

TIMING_CLOCK_LABELS = {
    "real": "real_monotonic_measured",
    "fake": "fake_clock_simulated",
}


def fold(text: str) -> str:
    """NFC + casefold, the shared comparison base for words and WER."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return unicodedata.normalize("NFC", text).casefold()


def normalize_token(word: str) -> str:
    """Word comparison form: NFC/casefold with punctuation removed."""
    return "".join(
        char
        for char in fold(word)
        if not unicodedata.category(char).startswith("P")
    )


def normalize_text(text: str) -> str:
    """WER normalizer v1 (see module docstring)."""
    replaced = "".join(
        " " if unicodedata.category(char).startswith("P") else char
        for char in fold(text)
    )
    return " ".join(replaced.split())


def normalize_tokens(text: str) -> list[str]:
    normalized = normalize_text(text)
    return normalized.split() if normalized else []


# ---------------------------------------------------------------------------
# WER alignment
# ---------------------------------------------------------------------------


def _operation(
    kind: str,
    *,
    reference: str | None,
    hypothesis: str | None,
    reference_index: int | None,
    hypothesis_index: int | None,
) -> dict:
    return {
        "op": kind,
        "reference": reference,
        "hypothesis": hypothesis,
        "reference_index": reference_index,
        "hypothesis_index": hypothesis_index,
    }


def align_tokens(
    reference: Sequence[str], hypothesis: Sequence[str]
) -> tuple[dict[str, int], list[dict]]:
    """Deterministic Levenshtein alignment.

    When edit costs tie the traceback prefers match, then substitution, then
    deletion, then insertion.  The returned operations are in reference order.
    """
    n = len(reference)
    m = len(hypothesis)
    costs = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        costs[i][0] = i
    for j in range(1, m + 1):
        costs[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if reference[i - 1] == hypothesis[j - 1]:
                costs[i][j] = costs[i - 1][j - 1]
            else:
                costs[i][j] = 1 + min(
                    costs[i - 1][j - 1],
                    costs[i - 1][j],
                    costs[i][j - 1],
                )

    operations: list[dict] = []
    i, j = n, m
    while i > 0 or j > 0:
        if (
            i > 0
            and j > 0
            and reference[i - 1] == hypothesis[j - 1]
            and costs[i][j] == costs[i - 1][j - 1]
        ):
            operations.append(
                _operation(
                    "match",
                    reference=reference[i - 1],
                    hypothesis=hypothesis[j - 1],
                    reference_index=i - 1,
                    hypothesis_index=j - 1,
                )
            )
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and costs[i][j] == costs[i - 1][j - 1] + 1:
            operations.append(
                _operation(
                    "substitution",
                    reference=reference[i - 1],
                    hypothesis=hypothesis[j - 1],
                    reference_index=i - 1,
                    hypothesis_index=j - 1,
                )
            )
            i -= 1
            j -= 1
        elif i > 0 and costs[i][j] == costs[i - 1][j] + 1:
            operations.append(
                _operation(
                    "deletion",
                    reference=reference[i - 1],
                    hypothesis=None,
                    reference_index=i - 1,
                    hypothesis_index=None,
                )
            )
            i -= 1
        else:
            operations.append(
                _operation(
                    "insertion",
                    reference=None,
                    hypothesis=hypothesis[j - 1],
                    reference_index=None,
                    hypothesis_index=j - 1,
                )
            )
            j -= 1
    operations.reverse()

    counts = {
        "substitutions": sum(1 for op in operations if op["op"] == "substitution"),
        "deletions": sum(1 for op in operations if op["op"] == "deletion"),
        "insertions": sum(1 for op in operations if op["op"] == "insertion"),
    }
    counts["errors"] = counts["substitutions"] + counts["deletions"] + counts["insertions"]
    return counts, operations


def wer(reference_text: str, hypothesis_text: str) -> dict:
    """Normalized WER record with raw text, normalized text, S/D/I and ops."""
    reference = normalize_tokens(reference_text)
    hypothesis = normalize_tokens(hypothesis_text)
    counts, operations = align_tokens(reference, hypothesis)
    reference_count = len(reference)
    return {
        "reference_text": reference_text,
        "hypothesis_text": hypothesis_text,
        "reference_normalized": normalize_text(reference_text),
        "hypothesis_normalized": normalize_text(hypothesis_text),
        "reference_tokens": reference_count,
        "hypothesis_tokens": len(hypothesis),
        "substitutions": counts["substitutions"],
        "deletions": counts["deletions"],
        "insertions": counts["insertions"],
        "errors": counts["errors"],
        "wer": None if reference_count == 0 else counts["errors"] / reference_count,
        "operations": operations,
    }


def micro_aggregate(results: Iterable[Any]) -> dict:
    """Micro-aggregate S/D/I over the summed reference count.

    Empty-reference trials still contribute their insertions and are counted
    separately; their per-trial WER remains null.  A macro mean is reported for
    context but is never substituted for the micro-aggregate.
    """
    entries = list(results)
    valid = [entry for entry in entries if isinstance(entry, dict)]
    reference_tokens = sum(int(entry.get("reference_tokens") or 0) for entry in valid)
    hypothesis_tokens = sum(int(entry.get("hypothesis_tokens") or 0) for entry in valid)
    substitutions = sum(int(entry.get("substitutions") or 0) for entry in valid)
    deletions = sum(int(entry.get("deletions") or 0) for entry in valid)
    insertions = sum(int(entry.get("insertions") or 0) for entry in valid)
    errors = substitutions + deletions + insertions

    ratios = [
        entry["wer"]
        for entry in valid
        if isinstance(entry.get("wer"), (int, float))
        and not isinstance(entry.get("wer"), bool)
        and math.isfinite(float(entry["wer"]))
    ]
    return {
        "trials": len(valid),
        "trials_missing": len(entries) - len(valid),
        "trials_with_reference": sum(
            1 for entry in valid if int(entry.get("reference_tokens") or 0) > 0
        ),
        "trials_empty_reference": sum(
            1 for entry in valid if int(entry.get("reference_tokens") or 0) == 0
        ),
        "reference_tokens": reference_tokens,
        "hypothesis_tokens": hypothesis_tokens,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "errors": errors,
        "micro_wer": None if reference_tokens == 0 else errors / reference_tokens,
        "macro_mean_wer": (
            None if not ratios else sum(float(value) for value in ratios) / len(ratios)
        ),
        "macro_trials": len(ratios),
    }


# ---------------------------------------------------------------------------
# Replay timing metrics
# ---------------------------------------------------------------------------


def _round_ms(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return round(number, 3)


def _event_output_text(event: dict) -> str:
    candidates = [event.get("text")]
    native = event.get("native") or {}
    if isinstance(native, dict):
        candidates.extend(
            [
                native.get("display_text"),
                native.get("tentative_text"),
                native.get("committed_text"),
            ]
        )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return ""


def _event_stable_text(event: dict, arm: str) -> str:
    if arm == "hybrid":
        policy_info = event.get("policy") or {}
        if isinstance(policy_info, dict):
            value = policy_info.get("stable_text")
            if isinstance(value, str) and value.strip():
                return value
        return ""
    if arm == "native-stream":
        native = event.get("native") or {}
        if isinstance(native, dict):
            value = native.get("committed_text")
            if isinstance(value, str) and value.strip():
                return value
    return ""


def compute_timings(
    events: Sequence[dict],
    *,
    audio_end_ms: float,
    arm: str,
    clock_mode: str,
) -> dict:
    """Compute per-trial timing metrics, labelled by clock source.

    Fake-clock values populate ``simulated`` only; ``measured`` stays null so a
    deterministic test can never be mistaken for real replay evidence.
    """
    if clock_mode not in TIMING_CLOCK_LABELS:
        raise ValueError(f"unsupported clock mode: {clock_mode!r}")

    partial_events = [
        event for event in events if event.get("kind") in ("partial", "feed")
    ]
    call_events = [
        event
        for event in events
        if event.get("kind") in ("partial", "feed", "endpoint", "final")
        and isinstance(event.get("timing"), dict)
    ]
    endpoint_events = [event for event in events if event.get("kind") == "endpoint"]
    final_events = [event for event in events if event.get("kind") == "final"]
    if arm == "endpoint" and not final_events:
        final_events = endpoint_events
    final_event = final_events[-1] if final_events else None

    first_partial = next(
        (event for event in partial_events if _event_output_text(event)), None
    )
    first_stable = next(
        (event for event in partial_events if _event_stable_text(event, arm)), None
    )

    if arm == "endpoint":
        first_partial_status = "unsupported_endpoint_arm_emits_no_partial_results"
        first_stable_status = "unsupported_endpoint_arm_has_no_stable_prefix"
    elif first_partial is None:
        first_partial_status = "no_nonempty_partial_result_before_final"
    else:
        first_partial_status = "observed"

    if arm == "endpoint":
        pass
    elif first_stable is not None:
        first_stable_status = "observed"
    elif arm == "native-stream":
        first_stable_status = "unsupported_or_not_observed_native_committed_text"
    else:
        first_stable_status = "no_stable_prefix_before_final"

    queue_lags = [
        value
        for value in (
            _round_ms((event.get("timing") or {}).get("queue_lag_ms"))
            for event in call_events
        )
        if value is not None
    ]
    backlogs = [
        int(value)
        for value in (
            (event.get("timing") or {}).get(
                "backlog_samples_after",
                (event.get("timing") or {}).get("backlog_samples"),
            )
            for event in call_events
        )
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    call_walls = [
        value
        for value in (
            _round_ms((event.get("timing") or {}).get("call_wall_ms"))
            for event in call_events
        )
        if value is not None
    ]
    native_decode_values = [
        _round_ms(event.get("decode_ms")) for event in call_events
    ]
    native_decode_known = [
        value
        for value in native_decode_values
        if value is not None and value > 0
    ]
    native_decode_unknown = sum(
        1
        for value in native_decode_values
        if value is None or value <= 0
    )
    coalesced_ticks = sum(
        len(event.get("coalesced_ticks") or []) for event in call_events
    )

    final_after_audio_end_ms: float | None = None
    final_after_audio_end_status = "no_final_event"
    final_call_wall_ms: float | None = None
    final_event_index: int | None = None
    if final_event is not None:
        timing = final_event.get("timing") or {}
        call_end = _round_ms(timing.get("call_end_ms"))
        if call_end is not None:
            final_after_audio_end_ms = round(call_end - float(audio_end_ms), 3)
            final_after_audio_end_status = "observed"
        else:
            final_after_audio_end_status = "missing_final_call_end"
        final_call_wall_ms = _round_ms(timing.get("call_wall_ms"))
        final_event_index = final_event.get("event_index")

    values = {
        "clock_source": TIMING_CLOCK_LABELS[clock_mode],
        "first_partial_ms": (
            _round_ms((first_partial.get("timing") or {}).get("call_end_ms"))
            if first_partial is not None
            else None
        ),
        "first_partial_status": first_partial_status,
        "first_stable_ms": (
            _round_ms((first_stable.get("timing") or {}).get("call_end_ms"))
            if first_stable is not None
            else None
        ),
        "first_stable_status": first_stable_status,
        "final_after_audio_end_ms": final_after_audio_end_ms,
        "final_after_audio_end_status": final_after_audio_end_status,
        "final_event_index": final_event_index,
        "decode_calls": len(call_events),
        "partial_calls": len(partial_events),
        "endpoint_calls": len(endpoint_events),
        "call_wall_total_ms": round(sum(call_walls), 3) if call_walls else None,
        "call_wall_max_ms": max(call_walls) if call_walls else None,
        "final_call_wall_ms": final_call_wall_ms,
        "queue_lag_max_ms": max(queue_lags) if queue_lags else None,
        "queue_lag_mean_ms": (
            round(sum(queue_lags) / len(queue_lags), 3) if queue_lags else None
        ),
        "backlog_max_samples": max(backlogs) if backlogs else None,
        "coalesced_ticks": coalesced_ticks,
        "native_decode_ms": {
            "known_values": len(native_decode_known),
            "unknown_values": native_decode_unknown,
            "total_ms": (
                round(sum(native_decode_known), 3) if native_decode_known else None
            ),
            "note": (
                "Native decode_ms is nullable and never inherited from stale "
                "batch timings; zero, negative and nonfinite values mean unknown "
                "and are not fabricated measurements."
            ),
        },
    }
    return {
        "clock_mode": clock_mode,
        "measured": values if clock_mode == "real" else None,
        "simulated": None if clock_mode == "real" else values,
        "word_end_latency_ms": None,
        "word_end_latency_status": WORD_END_LATENCY_STATUS,
    }


DEFINITIONS = {
    "wer_normalizer_v1": {
        "steps": [
            "Unicode NFC",
            "str.casefold()",
            "every Unicode punctuation character (general category P*) becomes a space",
            "whitespace collapsed to single spaces and trimmed",
            "accents and ñ preserved",
            "digits unchanged; no number expansion",
        ],
        "not_equivalent_to": "vendor-specific WER normalization",
    },
    "wer": {
        "formula": "(substitutions + deletions + insertions) / reference_token_count",
        "empty_reference": "WER is null; substitution/deletion/insertion counts are preserved",
        "alignment": (
            "deterministic Levenshtein; cost ties prefer match, then "
            "substitution, then deletion, then insertion"
        ),
        "reports": "per-trial S/D/I plus micro-aggregate errors/reference count",
    },
    "local_agreement_2": {
        "comparison": (
            "NFC/casefolded whitespace words with Unicode punctuation removed; "
            "accents and ñ preserved"
        ),
        "stability": (
            "words in the common prefix of two consecutive hypotheses; stable "
            "history is append-only"
        ),
        "conflicts": (
            "later conflicting hypotheses and final corrections are explicit "
            "events; they never rewrite confirmed stable history"
        ),
        "units": "runner word-level LA-2; native committed text is separate",
    },
    "native_committed_text": {
        "comparison": (
            "raw whitespace-canonicalized character prefix; native policy units "
            "are not assumed to equal runner words"
        ),
        "finalization": "final_text is authoritative even when committed history differs",
    },
    "timings": {
        "replay_start": (
            "t0 for all replay-relative fields; defined one sample period before "
            "the first fixture sample becomes available (sample i arrives at "
            "t0+(i+1)/sample_rate). first_partial_ms/first_stable_ms are "
            "conservatively high by 1/sample_rate (0.0625 ms at 16 kHz); the "
            "convention is retained for stability"
        ),
        "first_partial_ms": "first nonempty partial result arrival (call return) relative to replay start t0",
        "first_stable_ms": "first nonempty stable/committed result arrival relative to replay start t0",
        "final_after_audio_end_ms": "final call return minus fixture audio-end arrival",
        "call_wall_ms": (
            "runner monotonic elapsed around an engine call; includes validation/"
            "transport/native compute, not pure GPU decode time"
        ),
        "queue_lag_ms": "call start minus the selected scheduled tick/segment arrival",
        "backlog_samples": "audio available at call start beyond the frozen prefix",
        "backlog_samples_after": "audio available after the call beyond the frozen prefix",
        "coalesced_ticks": "scheduled partial/feed ticks superseded after a slow call",
        "native_decode_ms": (
            "nullable native decode component; zero, negative, nonfinite and "
            "absent values mean unknown and are never zero-filled"
        ),
        "fake_clock": "fake-clock values populate simulated fields only; measured stays null",
    },
    "aggregation": {
        "micro": "sum of S/D/I over sum of reference tokens; empty references count separately",
        "macro": "mean of per-trial WER ratios over trials with a nonempty reference; context only",
    },
    "unsupported": {
        "word_end_latency": WORD_END_LATENCY_STATUS,
        "rolling_window": (
            "long-call rollover/rolling windows are not implemented; fixtures "
            "above the configured max window are rejected rather than truncated"
        ),
        "endpoint_boundaries": (
            "fixture segment boundaries are oracle endpoints, not tested VAD"
        ),
    },
}
