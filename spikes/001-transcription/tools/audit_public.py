#!/usr/bin/env python3
"""Small stdlib-only public-artifact and Git-identity scanner.

This is deliberately a heuristic guard, not a substitute for human review.
It scans repository text for common private/credential shapes without printing
the matched value. Rule fragments are assembled at runtime so this file does
not match its own definitions when it is itself part of the scanned tree.

Usage from the repository root:

    python3 spikes/001-transcription/tools/audit_public.py
    python3 spikes/001-transcription/tools/audit_public.py --include-untracked
    python3 spikes/001-transcription/tools/audit_public.py path/to/candidate.md
    python3 spikes/001-transcription/tools/audit_public.py --git-identity \
        --require-expected-identity --expect-email owner@example.invalid

Additional forbidden domains or exact addresses can be supplied with
--forbid-domain/--forbid-email. Only the employer domain is a built-in rule; no
individual work or personal address is stored in this scanner.

Explicit path arguments support reviewed-but-not-yet-tracked files. The default
Git mode scans tracked files only; --include-untracked adds non-ignored
untracked files. Ignored caches, model weights and .omp state are not scanned.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

MAX_TEXT_BYTES = 4 * 1024 * 1024
SKIP_DIRS = {
    ".git",
    ".cache",
    ".tools",
    ".build",
    "build",
    ".omp",
    "worktrees",
    ".worktrees",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "scratch",
}

# The employer domain is an explicit task requirement. No individual work address,
# local part or personal address is stored here. The domain is composed only so the
# scanner does not match its own rule definition. Additional forbidden domains and
# exact addresses are supplied with --forbid-domain/--forbid-email or the API.
DEFAULT_FORBIDDEN_DOMAINS = ("luca" + "edu.com",)
DEFAULT_FORBIDDEN_EMAILS: tuple[str, ...] = ()
_PRIVATE_KEY_LABEL = "PRIVATE KEY"

_SIGNED_QUERY_KEYS = "|".join(
    [
        "X-Amz-Signature",
        "X-Amz-Credential",
        "X-Amz-Security-Token",
        "X-Goog-Signature",
        "X-Goog-Credential",
        "GoogleAccessId",
        "Signature",
        "sig",
        "token",
    ]
)


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    rule: str

    def as_dict(self) -> dict:
        return {"path": self.path, "line": self.line, "rule": self.rule}


@dataclass(frozen=True, order=True)
class Identity:
    name: str
    email: str
    role: str


class AuditError(RuntimeError):
    pass


def _normalize_values(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({value.strip().lower() for value in values if value.strip()}))


def _identity_patterns(
    forbidden_domains: Iterable[str],
    forbidden_emails: Iterable[str],
) -> list[tuple[str, re.Pattern[str]]]:
    patterns: list[tuple[str, re.Pattern[str]]] = []
    domains = _normalize_values(forbidden_domains)
    emails = _normalize_values(forbidden_emails)
    if domains:
        domain_alternatives = "|".join(re.escape(domain) for domain in domains)
        patterns.append(
            (
                "work_identity",
                re.compile(
                    r"\b[A-Za-z0-9._%+-]+@(?:" + domain_alternatives + r")\b",
                    re.IGNORECASE,
                ),
            )
        )
    if emails:
        email_alternatives = "|".join(re.escape(email) for email in emails)
        patterns.append(
            (
                "forbidden_identity",
                re.compile(
                    r"(?<![A-Za-z0-9._%+-])(?:"
                    + email_alternatives
                    + r")(?![A-Za-z0-9._%+-])",
                    re.IGNORECASE,
                ),
            )
        )
    return patterns


def build_rules(
    forbidden_domains: Iterable[str] = DEFAULT_FORBIDDEN_DOMAINS,
    forbidden_emails: Iterable[str] = DEFAULT_FORBIDDEN_EMAILS,
) -> list[tuple[str, re.Pattern[str]]]:
    rules: list[tuple[str, re.Pattern[str]]] = [
        (
            "private_home_path",
            re.compile(
                r"(?<![\w:.-])/(?:Users|home)/[A-Za-z0-9][A-Za-z0-9._-]*"
            ),
        ),
        (
            "private_home_relative_path",
            re.compile(r"(?<![\w])~[\\/](?:\.[A-Za-z0-9]|[A-Za-z0-9])[^\s\"'<>]*"),
        ),
        (
            "private_home_env_path",
            re.compile(
                r"(?:\$(?:\{HOME\}|HOME)|%USERPROFILE%)[\\/][^\s\"'<>]+",
                re.IGNORECASE,
            ),
        ),
        (
            "private_temporary_path",
            re.compile(
                r"(?<![\w:.-])/(?:private/)?var/folders/[A-Za-z0-9_]+/"
            ),
        ),
        (
            "windows_private_path",
            re.compile(r"[A-Za-z]:\\Users\\[^\\\s\"'<>]+"),
        ),
        (
            "signed_url",
            re.compile(
                r"[?&](?:" + _SIGNED_QUERY_KEYS + r")=[^&\s\"'<>]{12,}",
                re.IGNORECASE,
            ),
        ),
        ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
        (
            "github_token",
            re.compile(
                r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
            ),
        ),
        ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
        ("slack_token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}\b")),
        (
            "provider_secret_key",
            re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b"),
        ),
        (
            "private_key_block",
            re.compile(
                r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?"
                + _PRIVATE_KEY_LABEL
                + r"-----"
            ),
        ),
        (
            "bearer_token",
            re.compile(
                r"(?i)\bAuthorization\s*:\s*Bearer\s+[A-Za-z0-9._~+/-]{16,}={0,2}"
            ),
        ),
        (
            "credential_assignment",
            re.compile(
                r"(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|"
                r"secret[_-]?key|password|passwd)\s*[:=]\s*[\"']?"
                r"[A-Za-z0-9_./+=-]{16,}"
            ),
        ),
        (
            "invitation_link",
            re.compile(
                r"(?:meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}"
                r"|zoom\.us/j/\d{8,}"
                r"|calendar\.google\.com/calendar/event\?eid=[A-Za-z0-9_-]+"
                r"|hackerrank\.com/(?:interviews?|tests?|codepair)/[A-Za-z0-9_-]{10,})",
                re.IGNORECASE,
            ),
        ),
        (
            "calendar_event_id",
            re.compile(r"\b[a-z0-9]{20,32}@google\.com\b", re.IGNORECASE),
        ),
    ]
    rules.extend(_identity_patterns(forbidden_domains, forbidden_emails))
    return rules


RULES = build_rules()


def scan_text(
    text: str,
    display_path: str,
    *,
    rules: Sequence[tuple[str, re.Pattern[str]]] | None = None,
) -> list[Finding]:
    active_rules = RULES if rules is None else rules
    findings: set[Finding] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        for rule_name, pattern in active_rules:
            if pattern.search(line):
                findings.add(Finding(display_path, line_number, rule_name))
    return sorted(findings)


def _looks_binary(data: bytes) -> bool:
    return b"\x00" in data[:8192]


def display_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except (OSError, ValueError):
        return str(path)


def scan_file(
    path: Path,
    repo_root: Path,
    *,
    rules: Sequence[tuple[str, re.Pattern[str]]] | None = None,
) -> list[Finding]:
    try:
        if path.stat().st_size > MAX_TEXT_BYTES:
            return []
        data = path.read_bytes()
    except OSError as exc:
        raise AuditError(f"cannot read {path}: {exc}") from exc
    if _looks_binary(data):
        return []
    return scan_text(
        data.decode("utf-8", errors="replace"),
        display_path(path, repo_root),
        rules=rules,
    )


def _iter_directory(path: Path) -> Iterable[Path]:
    for current, dirnames, filenames in os.walk(path):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            yield Path(current) / filename


def expand_paths(paths: Sequence[Path], repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(_iter_directory(path))
        elif path.is_file():
            files.append(path)
        else:
            raise AuditError(f"path does not exist: {path}")
    return sorted({p.resolve() for p in files})


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise AuditError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result


def git_root(repo: Path) -> Path:
    result = _git(repo, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip())


def discover_git_files(repo: Path, *, include_untracked: bool) -> list[str]:
    args = ["ls-files", "-z", "--cached"]
    if include_untracked:
        args.extend(["--others", "--exclude-standard"])
    result = _git(repo, *args)
    entries = [entry for entry in result.stdout.split("\0") if entry]
    return sorted(set(entries))


def git_identity_entries(repo: Path) -> list[Identity]:
    format_string = "%an%x1f%ae%x1f%cn%x1f%ce"
    try:
        result = _git(repo, "log", "--all", "--format=" + format_string)
    except AuditError as exc:
        if "does not have any commits yet" in str(exc) or "your current branch" in str(exc):
            return []
        raise
    identities: set[Identity] = set()
    for line in result.stdout.splitlines():
        fields = line.split("\x1f")
        if len(fields) != 4:
            continue
        author_name, author_email, committer_name, committer_email = fields
        if author_email:
            identities.add(Identity(author_name, author_email, "author"))
        if committer_email:
            identities.add(Identity(committer_name, committer_email, "committer"))
    return sorted(identities)


def identity_findings(
    identities: Iterable[Identity],
    *,
    expected_emails: Iterable[str] = (),
    forbidden_domains: Iterable[str] = DEFAULT_FORBIDDEN_DOMAINS,
    forbidden_emails: Iterable[str] = DEFAULT_FORBIDDEN_EMAILS,
) -> list[Finding]:
    expected = _normalize_values(expected_emails)
    domains = _normalize_values(forbidden_domains)
    blocked_addresses = _normalize_values(forbidden_emails)
    findings: set[Finding] = set()
    for identity in identities:
        email = identity.email.lower()
        if any(email.endswith("@" + domain) for domain in domains):
            findings.add(Finding("git-identity", 0, "work_identity"))
        if email in blocked_addresses:
            findings.add(Finding("git-identity", 0, "forbidden_identity"))
        if expected and email not in expected:
            findings.add(Finding("git-identity", 0, "unexpected_git_identity"))
    return sorted(findings)


def _format_human(
    scanned: int,
    findings: Sequence[Finding],
    identities: Sequence[Identity],
    identity_findings_list: Sequence[Finding],
) -> str:
    lines = [f"scanned {scanned} file(s)"]
    if findings:
        lines.append(f"findings: {len(findings)}")
        lines.extend(f"{f.path}:{f.line}: {f.rule}" for f in findings)
    else:
        lines.append("no public-artifact findings")
    if identities:
        lines.append("git identities:")
        lines.extend(
            f"  {identity.role}: {identity.name} <{identity.email}>"
            for identity in identities
        )
    if identity_findings_list:
        lines.append(f"identity findings: {len(identity_findings_list)}")
        for finding in identity_findings_list:
            lines.append(f"git-identity: {finding.rule}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scan public-bound repository text for private paths, signed URLs, "
            "credentials, work identities and invitation-shaped links. "
            "Matched values are never printed."
        )
    )
    parser.add_argument("paths", nargs="*", help="explicit files/directories to scan")
    parser.add_argument("--repo", help="repository/root for path display and Git mode")
    parser.add_argument(
        "--include-untracked",
        action="store_true",
        help="include non-ignored untracked files in Git mode",
    )
    parser.add_argument(
        "--git-identity",
        action="store_true",
        help="audit author/committer identities from Git history",
    )
    parser.add_argument(
        "--expect-email",
        action="append",
        default=[],
        metavar="EMAIL",
        help="require every Git identity email to match (repeatable)",
    )
    parser.add_argument(
        "--require-expected-identity",
        action="store_true",
        help="with --git-identity, exit 2 unless --expect-email is supplied",
    )
    parser.add_argument(
        "--forbid-domain",
        action="append",
        default=[],
        metavar="DOMAIN",
        help="additional forbidden email domain (repeatable)",
    )
    parser.add_argument(
        "--forbid-email",
        action="append",
        default=[],
        metavar="EMAIL",
        help="additional forbidden exact email address (repeatable)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    if args.require_expected_identity and not args.git_identity:
        print(
            "audit error: --require-expected-identity requires --git-identity",
            file=sys.stderr,
        )
        return 2
    if args.require_expected_identity and not args.expect_email:
        print(
            "audit error: --require-expected-identity requires at least one "
            "--expect-email",
            file=sys.stderr,
        )
        return 2

    repo = Path(args.repo).resolve() if args.repo else Path.cwd().resolve()
    forbidden_domains = tuple(DEFAULT_FORBIDDEN_DOMAINS) + tuple(args.forbid_domain)
    forbidden_emails = tuple(DEFAULT_FORBIDDEN_EMAILS) + tuple(args.forbid_email)
    rules = build_rules(forbidden_domains, forbidden_emails)
    try:
        if args.paths:
            files = expand_paths([Path(p) for p in args.paths], repo)
        else:
            repo = git_root(repo)
            files = [
                (repo / entry).resolve()
                for entry in discover_git_files(
                    repo, include_untracked=args.include_untracked
                )
            ]
        findings = [
            finding
            for path in files
            for finding in scan_file(path, repo_root=repo, rules=rules)
        ]
        identities = git_identity_entries(repo) if args.git_identity else []
        identities_findings = (
            identity_findings(
                identities,
                expected_emails=args.expect_email,
                forbidden_domains=forbidden_domains,
                forbidden_emails=forbidden_emails,
            )
            if args.git_identity
            else []
        )
    except AuditError as exc:
        print(f"audit error: {exc}", file=sys.stderr)
        return 2

    all_findings = list(findings) + list(identities_findings)
    if args.json:
        payload = {
            "scanned_files": len(files),
            "scanned_paths": [display_path(path, repo) for path in files],
            "findings": [finding.as_dict() for finding in findings],
            "identities": [
                {"name": i.name, "email": i.email, "role": i.role}
                for i in identities
            ],
            "identity_findings": [
                finding.as_dict() for finding in identities_findings
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            _format_human(
                len(files),
                findings,
                identities,
                identities_findings,
            )
        )
    return 1 if all_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
