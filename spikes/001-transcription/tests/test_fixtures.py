"""Offline integrity tests for the licensed bilingual fixture slice.

These tests never touch the curated fixture bytes in place and never use the
network.  Structural mutations use in-memory manifests; byte-level mutations
use copies under a temporary directory.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import json
import shutil
import struct
import sys
import tarfile
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

SPIKE_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = SPIKE_ROOT / "fixtures"
sys.path.insert(0, str(FIXTURES))
sys.path.insert(0, str(SPIKE_ROOT / "tools"))

import fetch_fixtures  # noqa: E402
import manifest_tools  # noqa: E402

PINNED_REVISION = "70bb2e84b976b7e960aa89f1c648e09c59f894dd"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wav_bytes(*, channels: int = 1, sample_width: int = 2,
              sample_rate: int = 16000, frames: int = 1600) -> bytes:
    """A small deterministic integer-PCM WAV for negative format tests."""
    import io

    out = io.BytesIO()
    with wave.open(out, "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(sample_width)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00" * frames * channels * sample_width)
    return out.getvalue()


def float32_wav_bytes(samples: list[float], *, rate: int = 16000) -> bytes:
    """Build a WAVE_FORMAT_IEEE_FLOAT mono file with a fact chunk."""
    payload = struct.pack("<%df" % len(samples), *samples)
    fmt = struct.pack("<HHIIHH", 3, 1, rate, rate * 4, 4, 32)
    fact = struct.pack("<I", len(samples))
    chunks = (
        b"fmt " + struct.pack("<I", len(fmt)) + fmt
        + b"fact" + struct.pack("<I", len(fact)) + fact
        + b"data" + struct.pack("<I", len(payload)) + payload
    )
    riff_size = 4 + len(chunks)
    return b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + chunks


def tar_gz_bytes(members: dict[str, bytes]) -> bytes:
    """Build an in-memory gzip-compressed tar for extraction tests."""
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


def uncompressed_tar_bytes(name: str, data: bytes) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return output.getvalue()


class FakeResponse:
    """Minimal urllib response double that records whether the body was read."""

    def __init__(self, status: int, headers: dict[str, str], body: bytes = b"") -> None:
        self.status = status
        self.headers = headers
        self.body = body
        self.read_calls = 0

    def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        if size is None or size < 0:
            return self.body
        return self.body[:size]

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        return False


class FixtureTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = manifest_tools.load_manifest(
            FIXTURES / "manifest.json", SPIKE_ROOT
        )

    def temp_root(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        td = tempfile.TemporaryDirectory()
        root = Path(td.name)
        shutil.copytree(FIXTURES, root / "fixtures")
        return td, root

    def assert_fixture_error(self, manifest: dict, root: Path = SPIKE_ROOT) -> None:
        with self.assertRaises(manifest_tools.FixtureError):
            manifest_tools.validate_manifest(manifest, root)

    def test_real_manifest_is_valid_and_complete(self) -> None:
        fixtures = self.manifest["fixtures"]
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["sample_rate"], 16000)
        self.assertGreaterEqual(len(fixtures), 2)
        self.assertEqual(
            {fixture["language"] for fixture in fixtures}, {"en", "es", "mixed"}
        )
        self.assertEqual(
            {fixture["language"]: fixture["asr_language"] for fixture in fixtures},
            {"en": "en-US", "es": "es-US", "mixed": "auto"},
        )
        ids = [fixture["id"] for fixture in fixtures]
        self.assertEqual(len(ids), len(set(ids)))
        paths = [fixture["wav"] for fixture in fixtures]
        self.assertEqual(len(paths), len(set(paths)))
        for fixture in fixtures:
            self.assertRegex(fixture["id"], r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
            self.assertTrue(fixture["wav"].startswith("fixtures/"))
            self.assertTrue(fixture["reference"].startswith("fixtures/"))
            self.assertLessEqual(fixture["duration_s"], 20.0)
            self.assertEqual(fixture["source"]["license"], "CC-BY-4.0")
            self.assertEqual(fixture["source"]["revision"], PINNED_REVISION)
            self.assertEqual(fixture["source"]["reference_column"],
                             "raw_transcription")
            self.assertIn(PINNED_REVISION, fixture["source"]["url"])
            self.assertNotIn("?", fixture["source"]["url"])
            self.assertNotIn("X-Amz", fixture["source"]["url"])
            self.assertIn("stdlib", fixture["conversion"]["tool"])

    def test_original_clip_boundaries_are_oracle_endpoints(self) -> None:
        for fixture in self.manifest["fixtures"]:
            if fixture["id"].startswith("derived-"):
                continue
            self.assertEqual(len(fixture["segments"]), 1)
            segment = fixture["segments"][0]
            self.assertEqual(segment["kind"], "oracle_file_boundary")
            self.assertEqual(segment["start_s"], 0.0)
            self.assertAlmostEqual(segment["end_s"], fixture["duration_s"],
                                   places=3)

    def test_derived_assemblies_are_explicit_and_not_dataset_boundaries(self) -> None:
        derived = [f for f in self.manifest["fixtures"]
                   if f["id"].startswith("derived-")]
        self.assertGreaterEqual(len(derived), 2)
        for fixture in derived:
            self.assertGreater(len(fixture["segments"]), 1)
            self.assertEqual({s["kind"] for s in fixture["segments"]},
                             {"derived_assembly"})
            self.assertNotEqual(fixture["conversion"]["tool"], "none")

    def test_derived_references_are_explicitly_concatenated(self) -> None:
        derived = [f for f in self.manifest["fixtures"]
                   if f["id"].startswith("derived-")]
        originals = [f for f in self.manifest["fixtures"]
                     if not f["id"].startswith("derived-")]
        by_row = {f["source"]["row"]: f for f in originals}
        for fixture in derived:
            if "repeat" in fixture["id"]:
                source_text = (
                    SPIKE_ROOT / by_row[fixture["source"]["row"]]["reference"]
                ).read_text(encoding="utf-8").strip()
                expected = source_text + " " + source_text
            else:
                en_text = (
                    SPIKE_ROOT / by_row[fixture["source"]["row"]]["reference"]
                ).read_text(encoding="utf-8").strip()
                es_row = next(
                    f["source"]["row"] for f in originals if f["language"] == "es"
                )
                es_text = (
                    SPIKE_ROOT / by_row[es_row]["reference"]
                ).read_text(encoding="utf-8").strip()
                expected = en_text + " " + es_text
            actual = (
                SPIKE_ROOT / fixture["reference"]
            ).read_text(encoding="utf-8").strip()
            with self.subTest(fixture=fixture["id"]):
                self.assertEqual(actual, expected)

    def test_mixed_language_switch_fixture_is_explicit(self) -> None:
        fixtures = self.manifest["fixtures"]
        mixed = next(f for f in fixtures if f["id"] == "derived-en-us-es-419-switch")
        self.assertEqual(mixed["language"], "mixed")
        self.assertEqual(mixed["asr_language"], "auto")
        self.assertEqual([s["kind"] for s in mixed["segments"]],
                         ["derived_assembly", "derived_assembly"])
        originals = [f for f in fixtures if not f["id"].startswith("derived-")]
        en = next(f for f in originals if f["language"] == "en")
        es = next(f for f in originals if f["language"] == "es")
        en_info = manifest_tools.wav_info(SPIKE_ROOT / en["wav"])
        es_info = manifest_tools.wav_info(SPIKE_ROOT / es["wav"])
        mixed_info = manifest_tools.wav_info(SPIKE_ROOT / mixed["wav"])
        self.assertEqual(mixed_info["frames"], en_info["frames"] + es_info["frames"])
        self.assertAlmostEqual(
            mixed["duration_s"], en["duration_s"] + es["duration_s"], places=6
        )
        tool = mixed["conversion"]["tool"]
        self.assertEqual(tool, fetch_fixtures.MIXED_CONVERSION_TOOL)
        self.assertIn(
            "en_us:518:10233995782544396174.wav:"
            "bfa2f3fb72a05cbcb7c0000a460435f2d0eedca7c5cc90f01aacc89127df7f63",
            tool,
        )
        self.assertIn(
            "es_419:322:10149016836336603986.wav:"
            "13b06188bd62a1a63ed350e6fe1a1ee8518db1ea7bc8f75d72849ca023de7c32",
            tool,
        )
        self.assertEqual(mixed["source"]["row"], en["source"]["row"])
        readme = " ".join(
            (FIXTURES / "README.md").read_text(encoding="utf-8").lower().split()
        )
        self.assertIn("different recordings/speakers", readme)
        self.assertIn("not a natural mid-sentence", readme)

    def test_manifest_pins_source_hashes_and_rows(self) -> None:
        for fixture in self.manifest["fixtures"]:
            source = fixture["source"]
            self.assertRegex(source["audio_sha256"], r"^[0-9a-f]{64}$")
            self.assertGreaterEqual(source["row"], 0)
            self.assertTrue(source["item_id"].endswith(".wav"))
            self.assertEqual(source["split"], "test")
            self.assertIn(source["config"], {"en_us", "es_419"})
            self.assertEqual(source["locale"], source["config"])

    def test_unknown_fields_are_rejected(self) -> None:
        cases = []
        top = copy.deepcopy(self.manifest)
        top["unexpected"] = 1
        cases.append(top)
        entry = copy.deepcopy(self.manifest)
        entry["fixtures"][0]["unexpected"] = 1
        cases.append(entry)
        source = copy.deepcopy(self.manifest)
        source["fixtures"][0]["source"]["unexpected"] = 1
        cases.append(source)
        conversion = copy.deepcopy(self.manifest)
        conversion["fixtures"][0]["conversion"]["unexpected"] = 1
        cases.append(conversion)
        segment = copy.deepcopy(self.manifest)
        segment["fixtures"][0]["segments"][0]["unexpected"] = 1
        cases.append(segment)
        for manifest in cases:
            with self.subTest(manifest=manifest):
                self.assert_fixture_error(manifest)

    def test_missing_required_fields_are_rejected(self) -> None:
        for field in ("id", "language", "asr_language", "wav", "reference",
                      "wav_sha256", "reference_sha256", "duration_s",
                      "source", "conversion", "segments"):
            manifest = copy.deepcopy(self.manifest)
            del manifest["fixtures"][0][field]
            with self.subTest(field=field):
                self.assert_fixture_error(manifest)
        manifest = copy.deepcopy(self.manifest)
        del manifest["fixtures"][0]["source"]["row"]
        self.assert_fixture_error(manifest)

    def test_schema_version_and_sample_rate_are_pinned(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["schema_version"] = 2
        self.assert_fixture_error(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["sample_rate"] = 8000
        self.assert_fixture_error(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"] = []
        self.assert_fixture_error(manifest)

    def test_duplicate_ids_and_paths_are_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"][1]["id"] = manifest["fixtures"][0]["id"]
        self.assert_fixture_error(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"][1]["wav"] = manifest["fixtures"][0]["wav"]
        self.assert_fixture_error(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"][1]["reference"] = manifest["fixtures"][0]["reference"]
        self.assert_fixture_error(manifest)

    def test_unsafe_ids_are_rejected(self) -> None:
        for bad_id in ("", "../escape", "a/b", ".", "..", "a b", "-leading"):
            manifest = copy.deepcopy(self.manifest)
            manifest["fixtures"][0]["id"] = bad_id
            with self.subTest(bad_id=bad_id):
                self.assert_fixture_error(manifest)

    def test_path_traversal_absolute_and_backslash_are_rejected(self) -> None:
        for bad_path in ("../outside.wav", "/etc/hosts",
                         "fixtures\\..\\outside.wav", "fixtures//x.wav",
                         "fixtures/./x.wav", "C:/tmp/x.wav", ""):
            manifest = copy.deepcopy(self.manifest)
            manifest["fixtures"][0]["wav"] = bad_path
            with self.subTest(bad_path=bad_path):
                self.assert_fixture_error(manifest)

    def test_dot_component_path_is_rejected_even_when_it_resolves(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        entry = manifest["fixtures"][0]
        entry["wav"] = "fixtures/./" + Path(entry["wav"]).name
        self.assert_fixture_error(manifest)
        with self.assertRaisesRegex(manifest_tools.FixtureError,
                                    "traversal segments"):
            manifest_tools.resolve_manifest_path(
                SPIKE_ROOT, entry["wav"], "test.wav"
            )

    def test_symlink_alias_to_same_wav_is_rejected_as_duplicate_resolved_path(
        self,
    ) -> None:
        td, root = self.temp_root()
        self.addCleanup(td.cleanup)
        manifest = copy.deepcopy(self.manifest)
        entry = copy.deepcopy(manifest["fixtures"][0])
        alias_entry = copy.deepcopy(entry)
        alias_entry["id"] = "duplicate-resolved-path"
        alias_entry["wav"] = "fixtures/alias.wav"
        alias_entry["reference"] = "fixtures/alias_ref.txt"
        manifest["fixtures"] = [entry, alias_entry]
        (root / "fixtures" / "alias_ref.txt").write_bytes(
            (root / entry["reference"]).read_bytes()
        )
        try:
            (root / "fixtures" / "alias.wav").symlink_to(root / entry["wav"])
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        with self.assertRaisesRegex(manifest_tools.FixtureError,
                                    "duplicate resolved path"):
            manifest_tools.validate_manifest(manifest, root)

    def test_derived_assembly_requires_non_none_conversion(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        mixed = next(
            f for f in manifest["fixtures"]
            if f["id"] == "derived-en-us-es-419-switch"
        )
        mixed["conversion"]["tool"] = "none"
        self.assert_fixture_error(manifest)

        manifest = copy.deepcopy(self.manifest)
        entry = manifest["fixtures"][0]
        entry["segments"] = [
            {
                "start_s": 0.0,
                "end_s": entry["duration_s"],
                "kind": "derived_assembly",
            }
        ]
        entry["conversion"]["tool"] = "none"
        self.assert_fixture_error(manifest)

        manifest = copy.deepcopy(self.manifest)
        mixed = next(
            f for f in manifest["fixtures"]
            if f["id"] == "derived-en-us-es-419-switch"
        )
        mixed["conversion"]["tool"] = " none "
        self.assert_fixture_error(manifest)

    def test_escaping_symlink_is_rejected(self) -> None:
        td, root = self.temp_root()
        self.addCleanup(td.cleanup)
        outside_td = tempfile.TemporaryDirectory()
        self.addCleanup(outside_td.cleanup)
        # A valid WAV outside the temp spike root: if the confinement guard
        # regresses, hashing/format/duration checks would all succeed and only
        # this test's message assertion would catch it.
        outside = Path(outside_td.name) / "outside.wav"
        outside.write_bytes(wav_bytes())
        link = root / "fixtures" / "escape.wav"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"][0]["wav"] = "fixtures/escape.wav"
        manifest["fixtures"][0]["wav_sha256"] = sha256_bytes(outside.read_bytes())
        manifest["fixtures"][0]["duration_s"] = 0.1
        manifest["fixtures"][0]["segments"][0]["end_s"] = 0.1
        with self.assertRaisesRegex(manifest_tools.FixtureError,
                                    "escapes spike root"):
            manifest_tools.validate_manifest(manifest, root)

    def test_corrupt_copied_wav_fails_hash_and_original_is_untouched(self) -> None:
        td, root = self.temp_root()
        self.addCleanup(td.cleanup)
        entry = self.manifest["fixtures"][0]
        original = SPIKE_ROOT / entry["wav"]
        before = sha256_bytes(original.read_bytes())
        target = root / entry["wav"]
        data = bytearray(target.read_bytes())
        data[len(data) // 2] ^= 0x01
        target.write_bytes(bytes(data))
        with self.assertRaisesRegex(manifest_tools.FixtureError, "sha256"):
            manifest_tools.validate_manifest(self.manifest, root)
        self.assertEqual(before, sha256_bytes(original.read_bytes()))

    def test_corrupt_copied_reference_fails_hash(self) -> None:
        td, root = self.temp_root()
        self.addCleanup(td.cleanup)
        entry = self.manifest["fixtures"][0]
        target = root / entry["reference"]
        target.write_bytes(target.read_bytes() + b"tamper\n")
        with self.assertRaisesRegex(manifest_tools.FixtureError, "sha256"):
            manifest_tools.validate_manifest(self.manifest, root)

    def test_bad_reference_encoding_and_empty_reference_are_rejected(self) -> None:
        td, root = self.temp_root()
        self.addCleanup(td.cleanup)
        manifest = copy.deepcopy(self.manifest)
        entry = manifest["fixtures"][0]
        target = root / entry["reference"]
        target.write_bytes(b"\xff\xfe\x00")
        entry["reference_sha256"] = sha256_bytes(target.read_bytes())
        self.assert_fixture_error(manifest, root)
        target.write_bytes(b"   \n")
        entry["reference_sha256"] = sha256_bytes(target.read_bytes())
        self.assert_fixture_error(manifest, root)

    def test_wav_format_guards(self) -> None:
        cases = (
            ("stereo", wav_bytes(channels=2), 1600 / 16000),
            ("rate", wav_bytes(sample_rate=8000), 1600 / 8000),
            ("width", wav_bytes(sample_width=4), 1600 / 16000),
        )
        for name, data, duration in cases:
            with self.subTest(name=name):
                td, root = self.temp_root()
                self.addCleanup(td.cleanup)
                manifest = copy.deepcopy(self.manifest)
                entry = manifest["fixtures"][0]
                target = root / entry["wav"]
                target.write_bytes(data)
                entry["wav_sha256"] = sha256_bytes(data)
                entry["duration_s"] = duration
                entry["segments"][0]["end_s"] = duration
                self.assert_fixture_error(manifest, root)

    def test_duration_mismatch_is_rejected(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        entry = manifest["fixtures"][0]
        entry["duration_s"] += 0.5
        entry["segments"][0]["end_s"] = entry["duration_s"]
        self.assert_fixture_error(manifest)

    def test_segment_bounds_coverage_and_kinds(self) -> None:
        mutations = []
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"][0]["segments"][0]["start_s"] = 0.1
        mutations.append(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"][0]["segments"][0]["end_s"] -= 0.1
        mutations.append(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"][0]["segments"][0]["kind"] = "word_timing"
        mutations.append(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"][0]["segments"].append(
            {"start_s": 0.0, "end_s": 0.1, "kind": "oracle_file_boundary"}
        )
        mutations.append(manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["fixtures"][0]["segments"][0]["start_s"] = float("inf")
        mutations.append(manifest)
        manifest = copy.deepcopy(self.manifest)
        derived = next(f for f in manifest["fixtures"] if "repeat" in f["id"])
        derived["segments"][0]["kind"] = "oracle_file_boundary"
        mutations.append(manifest)
        for manifest in mutations:
            with self.subTest(manifest=manifest["fixtures"][0]["segments"]):
                self.assert_fixture_error(manifest)

        manifest = copy.deepcopy(self.manifest)
        derived = next(f for f in manifest["fixtures"] if "repeat" in f["id"])
        derived["segments"][1]["start_s"] += 0.25
        mutations.append(manifest)
        self.assert_fixture_error(manifest)

    def test_nonfinite_json_is_rejected(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "manifest.json"
        text = json.dumps(self.manifest).replace(
            f'"duration_s": {self.manifest["fixtures"][0]["duration_s"]}',
            '"duration_s": NaN',
            1,
        )
        self.assertIn("NaN", text)
        path.write_text(text, encoding="utf-8")
        with self.assertRaises(manifest_tools.FixtureError):
            manifest_tools.load_manifest(path, SPIKE_ROOT)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "manifest.json"
        text = '{"schema_version": 1, "schema_version": 1, "sample_rate": 16000, "fixtures": []}'
        path.write_text(text, encoding="utf-8")
        with self.assertRaisesRegex(manifest_tools.FixtureError, "duplicate JSON key"):
            manifest_tools.load_manifest(path, SPIKE_ROOT)

    def test_documented_license_and_source_are_present(self) -> None:
        notice = (FIXTURES / "NOTICE-FLEURS-CC-BY-4.0.txt").read_text(
            encoding="utf-8"
        )
        readme = (FIXTURES / "README.md").read_text(encoding="utf-8")
        for text in (notice, readme):
            self.assertIn("CC BY 4.0", text)
            self.assertIn("FLEURS", text)
            self.assertIn(PINNED_REVISION, text)
            self.assertIn("https://creativecommons.org/licenses/by/4.0/", text)
        self.assertIn("regenerat", readme.lower())
        self.assertIn("oracle", readme.lower())


class FetchToolTestCase(unittest.TestCase):
    def test_pinned_source_contract(self) -> None:
        self.assertEqual(fetch_fixtures.REVISION, PINNED_REVISION)
        self.assertEqual(set(fetch_fixtures.SOURCES), {"en_us", "es_419"})
        for config, source in fetch_fixtures.SOURCES.items():
            self.assertEqual(config, source.config)
            self.assertEqual(source.split, "test")
            self.assertEqual(source.license, "CC-BY-4.0")
            self.assertIn(PINNED_REVISION, source.tar_url)
            self.assertGreaterEqual(source.prefix_bytes, 4 * 1024 * 1024)
            self.assertLessEqual(source.prefix_bytes, 8 * 1024 * 1024)

    def test_content_range_parser_accepts_only_satisfied_ranges(self) -> None:
        self.assertEqual(
            fetch_fixtures.parse_content_range("bytes 0-8388607/289851356"),
            (0, 8388607, 289851356),
        )
        for bad in ("bytes */289851356", "bytes 1-2/10", "items 0-2/10", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(fetch_fixtures.FetchError):
                    fetch_fixtures.parse_content_range(bad)

    def test_fetch_prefix_rejects_non_206_without_reading_body(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        response = FakeResponse(200, {"Content-Range": "bytes 0-99/100"},
                                b"full archive must not be read")
        with mock.patch.object(fetch_fixtures, "_http_open", return_value=response):
            with self.assertRaisesRegex(fetch_fixtures.FetchError,
                                        "did not honour bounded Range"):
                fetch_fixtures._fetch_prefix(
                    fetch_fixtures.SOURCES["en_us"],
                    Path(td.name),
                    fetch_fixtures.MIN_PREFIX_BYTES,
                )
        self.assertEqual(response.read_calls, 0)

    def test_fetch_prefix_rejects_bad_content_range_without_reading_body(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        response = FakeResponse(206, {"Content-Range": "bytes 0-99/123"}, b"x")
        with mock.patch.object(fetch_fixtures, "_http_open", return_value=response):
            with self.assertRaisesRegex(fetch_fixtures.FetchError,
                                        "unexpected source size"):
                fetch_fixtures._fetch_prefix(
                    fetch_fixtures.SOURCES["en_us"],
                    Path(td.name),
                    fetch_fixtures.MIN_PREFIX_BYTES,
                )
        self.assertEqual(response.read_calls, 0)

    def test_extract_complete_members_accepts_complete_member_before_tail(self) -> None:
        wanted = b"W" * 1000
        # Incompressible filler makes it safe to truncate compressed bytes
        # after the complete wanted member.
        filler = bytes(range(256)) * 100
        full = tar_gz_bytes({"wanted.wav": wanted, "later.wav": filler * 100})
        prefix = full[:-2000]
        found = fetch_fixtures.extract_complete_members(prefix, {"wanted.wav"})
        self.assertEqual(found, {"wanted.wav": wanted})

    def test_extract_complete_members_rejects_truncated_member(self) -> None:
        # A valid gzip stream over an uncompressed tar whose data payload was
        # cut short: the tar header still announces the original size.
        tar_bytes = uncompressed_tar_bytes("wanted.wav", b"W" * 4096)
        # 512-byte tar header plus the first quarter of the declared payload.
        truncated = tar_bytes[: 512 + 1024]
        prefix = gzip.compress(truncated)
        with self.assertRaisesRegex(
            fetch_fixtures.FetchError,
            "truncated tar member|bounded tar prefix",
        ):
            fetch_fixtures.extract_complete_members(prefix, {"wanted.wav"})

    def test_extract_complete_members_rejects_missing_member(self) -> None:
        prefix = tar_gz_bytes({"other.wav": b"other"})
        with self.assertRaisesRegex(fetch_fixtures.FetchError,
                                    "not found in bounded tar prefix"):
            fetch_fixtures.extract_complete_members(prefix, {"wanted.wav"})

    def test_write_if_unchanged_refuses_tampering_unless_forced(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        path = Path(td.name) / "fixture.wav"
        path.write_bytes(b"old")
        with self.assertRaisesRegex(fetch_fixtures.FetchError, "refus"):
            fetch_fixtures.write_if_unchanged(path, b"new", force=False)
        self.assertEqual(path.read_bytes(), b"old")
        self.assertEqual(fetch_fixtures.write_if_unchanged(path, b"old"), "unchanged")
        self.assertEqual(fetch_fixtures.write_if_unchanged(path, b"new", force=True),
                         "written")
        self.assertEqual(path.read_bytes(), b"new")
        fresh = Path(td.name) / "fresh.bin"
        self.assertEqual(fetch_fixtures.write_if_unchanged(fresh, b"data"), "written")

    def test_preflight_refuses_without_partial_writes(self) -> None:
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        good = root / "good.wav"
        bad = root / "bad.wav"
        bad.write_bytes(b"curated")
        with self.assertRaisesRegex(fetch_fixtures.FetchError, "refus"):
            fetch_fixtures._write_outputs({good: b"new", bad: b"changed"}, force=False)
        self.assertFalse(good.exists())
        self.assertEqual(bad.read_bytes(), b"curated")

    def test_float32_conversion_is_pcm16_mono_16k_and_clipped(self) -> None:
        samples = [0.0, 0.5, -0.5, 1.0, -1.0, 2.0, -2.0]
        output = fetch_fixtures.convert_float32_wav_to_pcm16(
            float32_wav_bytes(samples)
        )
        import io

        with wave.open(io.BytesIO(output), "rb") as handle:
            self.assertEqual(handle.getnchannels(), 1)
            self.assertEqual(handle.getsampwidth(), 2)
            self.assertEqual(handle.getframerate(), 16000)
            self.assertEqual(handle.getnframes(), len(samples))
            raw = handle.readframes(len(samples))
        values = struct.unpack("<%dh" % len(samples), raw)
        expected = [0, 16384, -16384, 32767, -32767, 32767, -32767]
        self.assertEqual(list(values), expected)

    def test_conversion_rejects_non_float_source(self) -> None:
        with self.assertRaises(fetch_fixtures.FetchError):
            fetch_fixtures.convert_float32_wav_to_pcm16(wav_bytes())


if __name__ == "__main__":
    unittest.main()
