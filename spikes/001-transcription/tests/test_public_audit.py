"""Red/green and regression tests for the small public-artifact scanner.

Sensitive samples are assembled at runtime or use reserved example domains so this
test file can itself be included in a public-artifact scan. No real credential, work
address or personal address is stored here.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SPIKE_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = SPIKE_ROOT / "tools" / "audit_public.py"

_spec = importlib.util.spec_from_file_location("escalier_audit_public", AUDIT_PATH)
audit = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = audit
_spec.loader.exec_module(audit)

SYNTHETIC_FORBIDDEN_DOMAIN = "corp" + ".example"
SYNTHETIC_WORK_EMAIL = "operator@" + SYNTHETIC_FORBIDDEN_DOMAIN
SYNTHETIC_EXPECTED_EMAIL = "owner" + "@example.invalid"
SYNTHETIC_UNEXPECTED_EMAIL = "outsider" + "@example.invalid"
SYNTHETIC_FORBIDDEN_ADDRESS = "reviewer" + "@example.invalid"


def _synthetic_rules(*, forbidden_emails: tuple[str, ...] = ()) -> list:
    return audit.build_rules((SYNTHETIC_FORBIDDEN_DOMAIN,), forbidden_emails)


def _scan_text(text: str, *, forbidden_emails: tuple[str, ...] = ()) -> list:
    return audit.scan_text(
        text, "sample.txt", rules=_synthetic_rules(forbidden_emails=forbidden_emails)
    )


def _scan_default(text: str) -> list:
    return audit.scan_text(text, "sample.txt")


def _private_home_path() -> str:
    return "/" + "Users/" + "example-person/project/file.txt"


def _private_temporary_path() -> str:
    return "/" + "private/" + "var/folders/aa/bb/T/session"


def _windows_private_path() -> str:
    return "C:" + "\\" + "Users" + "\\" + "example-person\\project"


def _github_token() -> str:
    return "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


def _aws_key() -> str:
    return "AK" + "IA" + "A" * 16


def _private_key_block() -> str:
    return "-----BEGIN " + "OPENSSH " + "PRIVATE KEY-----\nnot-a-real-key\n"


def _signed_url() -> str:
    return (
        "https://storage.example.invalid/object?X-Amz-"
        + "Signature="
        + "a" * 32
        + "&X-Amz-Expires=60"
    )


def _calendar_link() -> str:
    return "https://meet." + "google.com/" + "abc-defg-hij"


def _run_cli(repo: Path, *args: str, paths: tuple[Path, ...] = ()) -> subprocess.CompletedProcess:
    command = [
        sys.executable,
        str(AUDIT_PATH),
        "--repo",
        str(repo),
        *args,
        *[str(path) for path in paths],
    ]
    return subprocess.run(command, capture_output=True, text=True, check=False)


def _make_repo(tmp: str, author_email: str, committer_email: str) -> Path:
    repo = Path(tmp)
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    tracked = repo / "tracked.md"
    tracked.write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "tracked.md"], check=True)
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Synthetic Author",
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_COMMITTER_NAME": "Synthetic Committer",
            "GIT_COMMITTER_EMAIL": committer_email,
        }
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Synthetic",
            "-c",
            "user.email=owner" + "@example.invalid",
            "commit",
            "-qm",
            "synthetic commit",
        ],
        env=env,
        check=True,
    )
    return repo


class DetectionTests(unittest.TestCase):
    def test_clean_text_does_not_fail_ignore_policy_or_rule_words(self) -> None:
        clean = (
            "Keep agent state in .omp/, source caches in .cache/ and .tools/, "
            "and builds in .build/.\n"
            "The document may name /Users and PRIVATE KEY as literal words.\n"
            "A public support URL is https://support.hackerrank.com/articles/123.\n"
            "A static asset may carry a public expiry: "
            "https://static.example.invalid/app.js?Expires=253370764800.\n"
            "An ordinary public contact is maintainer@example.org.\n"
            "The generic documentation form ~/... is not an owner path.\n"
        )
        self.assertEqual(_scan_text(clean), [])

    def test_scanner_source_and_this_test_do_not_self_match(self) -> None:
        for path in (AUDIT_PATH, Path(__file__).resolve()):
            self.assertEqual(audit.scan_file(path, repo_root=SPIKE_ROOT), [])

    def test_private_home_path_is_rejected(self) -> None:
        findings = _scan_text("saved under " + _private_home_path() + "\n")
        self.assertEqual([f.rule for f in findings], ["private_home_path"])

    def test_home_relative_and_environment_paths_are_rejected(self) -> None:
        cases = [
            ("~" + "/Library/Application Support/app", "private_home_relative_path"),
            ("~" + "/.cache/huggingface/models", "private_home_relative_path"),
            ("$" + "HOME/models/parakeet.gguf", "private_home_env_path"),
            ("$" + "{HOME}/models/parakeet.gguf", "private_home_env_path"),
            ("%USERPROFILE%" + "\\AppData\\Roaming\\app", "private_home_env_path"),
        ]
        for sample, expected_rule in cases:
            with self.subTest(sample=sample):
                rules = {finding.rule for finding in _scan_default(sample)}
                self.assertIn(expected_rule, rules)

    def test_private_temporary_path_is_rejected(self) -> None:
        findings = _scan_default("temporary " + _private_temporary_path() + "\n")
        self.assertIn("private_temporary_path", {finding.rule for finding in findings})

    def test_windows_private_path_is_rejected(self) -> None:
        findings = _scan_default("saved under " + _windows_private_path() + "\n")
        self.assertEqual([f.rule for f in findings], ["windows_private_path"])

    def test_signed_url_is_rejected(self) -> None:
        findings = _scan_text(_signed_url() + "\n")
        self.assertIn("signed_url", [f.rule for f in findings])

    def test_work_identity_domain_is_rejected(self) -> None:
        findings = _scan_text("contact " + SYNTHETIC_WORK_EMAIL + "\n")
        self.assertIn("work_identity", [f.rule for f in findings])

    def test_exact_forbidden_identity_is_rejected(self) -> None:
        findings = _scan_text(
            "contact " + SYNTHETIC_FORBIDDEN_ADDRESS + "\n",
            forbidden_emails=(SYNTHETIC_FORBIDDEN_ADDRESS,),
        )
        self.assertIn("forbidden_identity", [f.rule for f in findings])

    def test_common_secret_shapes_are_rejected(self) -> None:
        cases = {
            "github_token": _github_token(),
            "aws_access_key": _aws_key(),
            "private_key_block": _private_key_block(),
            "bearer_token": "Authorization: Bearer " + "x" * 24,
            "google_api_key": "AI" + "za" + "A" * 32,
            "slack_token": "xox" + "b-" + "A" * 12,
            "provider_secret_key": "sk-" + "proj-" + "A" * 24,
            "credential_assignment": "api_key = " + "A" * 24,
        }
        text = "\n".join(cases.values()) + "\n"
        rules = {finding.rule for finding in _scan_default(text)}
        self.assertEqual(set(cases), rules)

    def test_invitation_link_and_calendar_event_id_are_rejected(self) -> None:
        calendar_id = "a" * 26 + "@" + "google.com"
        findings = _scan_default(_calendar_link() + "\n" + calendar_id + "\n")
        rules = {finding.rule for finding in findings}
        self.assertIn("invitation_link", rules)
        self.assertIn("calendar_event_id", rules)

    def test_binary_content_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "blob.bin"
            path.write_bytes(b"\x00\x01" + _private_home_path().encode())
            self.assertEqual(audit.scan_file(path, repo_root=Path(tmp)), [])


class RepositoryInputTests(unittest.TestCase):
    def test_explicit_untracked_file_is_scanned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "candidate.md"
            path.write_text(_private_home_path() + "\n", encoding="utf-8")
            findings = audit.scan_file(path, repo_root=Path(tmp))
            self.assertEqual([f.rule for f in findings], ["private_home_path"])

    def test_untracked_file_requires_include_untracked_in_git_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            (repo / "tracked.md").write_text("clean\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "tracked.md"], check=True)
            (repo / "candidate.md").write_text(
                _private_home_path() + "\n", encoding="utf-8"
            )
            tracked_only = audit.discover_git_files(repo, include_untracked=False)
            self.assertEqual(tracked_only, ["tracked.md"])
            with_untracked = audit.discover_git_files(repo, include_untracked=True)
            self.assertEqual(sorted(with_untracked), ["candidate.md", "tracked.md"])

            result = _run_cli(repo, "--include-untracked", "--json")
            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["findings"][0]["path"], "candidate.md")
            self.assertEqual(payload["findings"][0]["rule"], "private_home_path")

    def test_human_output_never_echoes_the_matched_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "candidate.md"
            path.write_text(SYNTHETIC_WORK_EMAIL + "\n", encoding="utf-8")
            result = _run_cli(
                repo,
                "--forbid-domain",
                SYNTHETIC_FORBIDDEN_DOMAIN,
                paths=(path,),
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("work_identity", result.stdout)
            self.assertNotIn(SYNTHETIC_WORK_EMAIL, result.stdout)

    def test_cli_forbid_email_option_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "candidate.md"
            path.write_text(SYNTHETIC_FORBIDDEN_ADDRESS + "\n", encoding="utf-8")
            result = _run_cli(
                repo,
                "--forbid-email",
                SYNTHETIC_FORBIDDEN_ADDRESS,
                "--json",
                paths=(path,),
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["findings"][0]["rule"], "forbidden_identity")

    def test_cli_json_reports_findings_without_matching_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            path = repo / "candidate.md"
            path.write_text(SYNTHETIC_WORK_EMAIL + "\n", encoding="utf-8")
            result = _run_cli(
                repo,
                "--forbid-domain",
                SYNTHETIC_FORBIDDEN_DOMAIN,
                "--json",
                paths=(path,),
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["findings"][0]["rule"], "work_identity")
            self.assertNotIn(SYNTHETIC_WORK_EMAIL, result.stdout)
            self.assertEqual(payload["scanned_files"], 1)

    def test_git_identity_entries_parses_author_and_committer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(
                tmp, SYNTHETIC_EXPECTED_EMAIL, SYNTHETIC_UNEXPECTED_EMAIL
            )
            identities = audit.git_identity_entries(repo)
            self.assertIn(
                audit.Identity("Synthetic Author", SYNTHETIC_EXPECTED_EMAIL, "author"),
                identities,
            )
            self.assertIn(
                audit.Identity(
                    "Synthetic Committer", SYNTHETIC_UNEXPECTED_EMAIL, "committer"
                ),
                identities,
            )

    def test_git_identity_audit_flags_work_identity_but_allows_personal(self) -> None:
        personal = [
            audit.Identity("owner", SYNTHETIC_EXPECTED_EMAIL, "author"),
            audit.Identity("owner", SYNTHETIC_EXPECTED_EMAIL, "committer"),
        ]
        self.assertEqual(audit.identity_findings(personal), [])

        work = personal + [
            audit.Identity("owner", SYNTHETIC_WORK_EMAIL, "committer")
        ]
        rules = {
            finding.rule
            for finding in audit.identity_findings(
                work, forbidden_domains=(SYNTHETIC_FORBIDDEN_DOMAIN,)
            )
        }
        self.assertIn("work_identity", rules)

        exact = [
            audit.Identity("owner", SYNTHETIC_FORBIDDEN_ADDRESS, "author")
        ]
        exact_rules = {
            finding.rule
            for finding in audit.identity_findings(
                exact, forbidden_emails=(SYNTHETIC_FORBIDDEN_ADDRESS,)
            )
        }
        self.assertIn("forbidden_identity", exact_rules)

    def test_expected_identity_option_is_enforced(self) -> None:
        identities = [
            audit.Identity("owner", SYNTHETIC_EXPECTED_EMAIL, "author")
        ]
        findings = audit.identity_findings(
            identities, expected_emails={SYNTHETIC_UNEXPECTED_EMAIL}
        )
        self.assertIn(
            "unexpected_git_identity", {finding.rule for finding in findings}
        )

    def test_cli_requires_expected_identity_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(
                tmp, SYNTHETIC_EXPECTED_EMAIL, SYNTHETIC_EXPECTED_EMAIL
            )
            result = _run_cli(
                repo, "--git-identity", "--require-expected-identity"
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--expect-email", result.stderr)

    def test_cli_accepts_expected_author_and_committer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(
                tmp, SYNTHETIC_EXPECTED_EMAIL, SYNTHETIC_EXPECTED_EMAIL
            )
            result = _run_cli(
                repo,
                "--git-identity",
                "--require-expected-identity",
                "--expect-email",
                SYNTHETIC_EXPECTED_EMAIL,
                "--forbid-domain",
                SYNTHETIC_FORBIDDEN_DOMAIN,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cli_flags_unexpected_author(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(
                tmp, SYNTHETIC_UNEXPECTED_EMAIL, SYNTHETIC_EXPECTED_EMAIL
            )
            result = _run_cli(
                repo,
                "--git-identity",
                "--require-expected-identity",
                "--expect-email",
                SYNTHETIC_EXPECTED_EMAIL,
                "--json",
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn(
                "unexpected_git_identity",
                {finding["rule"] for finding in payload["identity_findings"]},
            )

    def test_cli_flags_unexpected_committer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(
                tmp, SYNTHETIC_EXPECTED_EMAIL, SYNTHETIC_UNEXPECTED_EMAIL
            )
            result = _run_cli(
                repo,
                "--git-identity",
                "--require-expected-identity",
                "--expect-email",
                SYNTHETIC_EXPECTED_EMAIL,
                "--json",
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn(
                "unexpected_git_identity",
                {finding["rule"] for finding in payload["identity_findings"]},
            )

    def test_cli_flags_forbidden_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_repo(tmp, SYNTHETIC_WORK_EMAIL, SYNTHETIC_WORK_EMAIL)
            result = _run_cli(
                repo,
                "--git-identity",
                "--require-expected-identity",
                "--expect-email",
                SYNTHETIC_EXPECTED_EMAIL,
                "--forbid-domain",
                SYNTHETIC_FORBIDDEN_DOMAIN,
                "--json",
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn(
                "work_identity",
                {finding["rule"] for finding in payload["identity_findings"]},
            )

    def test_git_identity_unborn_repository_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            self.assertEqual(audit.git_identity_entries(repo), [])
            result = _run_cli(
                repo,
                "--git-identity",
                "--require-expected-identity",
                "--expect-email",
                SYNTHETIC_EXPECTED_EMAIL,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
