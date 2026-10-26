#!/usr/bin/env python3
"""Build the pinned transcribe.cpp engine for spike 001.

The engine source is cloned into the spike's ignored ``.tools/`` directory and
built out-of-tree into ``.tools/build``.  Nothing is installed on the host and
no model is downloaded.  The pinned revision, vendored ggml provenance, patch
tree, build flags, and the resulting shared-library hash are written to
``.tools/build/engine-build.json``.  ``engine.lock.json`` records the reviewed
pin and artifact hash that the runtime adapter verifies.

Typical use from the repository root::

    python3 spikes/001-transcription/tools/build_engine.py
    python3 spikes/001-transcription/tools/build_engine.py --verify-only
    python3 spikes/001-transcription/tools/build_engine.py --import-check

The import check only loads the native library and enumerates ggml devices; it
does not load a model or run inference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ENGINE_REPOSITORY = "https://github.com/handy-computer/transcribe.cpp"
ENGINE_REVISION = "8facde6fcd8fb9caa585a5788ab450df6e8ec7db"
ENGINE_VERSION = "0.4.1"

#: Vendored ggml provenance recorded by the pinned revision itself.
EXPECTED_GGML_UPSTREAM_REPOSITORY = "git@github.com:ggml-org/ggml.git"
EXPECTED_GGML_UPSTREAM_SHA = "d7cb574130e6f01ad25b3289685489200febcd74"
EXPECTED_GGML_TREE = "417a338844d35617ec0cc5fd70ee39b0f98cd93f"
EXPECTED_PATCH_TREE = "ed9971fde1a4137415f891fb1a41647f2bd6609d"
EXPECTED_ABI_HASH = "f99ad4169374b8f3"

SPIKE_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = SPIKE_ROOT / ".tools"
SOURCE_DIR = TOOLS_DIR / "transcribe.cpp"
BUILD_DIR = TOOLS_DIR / "build"
BUILD_METADATA_PATH = BUILD_DIR / "engine-build.json"
LOCK_PATH = SPIKE_ROOT / "engine.lock.json"
BINDING_SRC = SOURCE_DIR / "bindings" / "python" / "src"

_LIBRARY_FILENAMES = (
    "libtranscribe.dylib",
    "libtranscribe.so",
    "transcribe.dll",
)


class BuildError(RuntimeError):
    """A pin, clean-tree, configure, build, or artifact check failed."""


def _library_filename() -> str:
    if sys.platform == "darwin":
        return "libtranscribe.dylib"
    if sys.platform == "win32":
        return "transcribe.dll"
    return "libtranscribe.so"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: int | None = None,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            args,
            cwd=str(cwd) if cwd is not None else None,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BuildError(f"could not run {shlex.join(args)}: {exc}") from exc


def _require_ok(proc: subprocess.CompletedProcess, what: str) -> str:
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise BuildError(f"{what} failed (exit {proc.returncode}): {detail[-4000:]}")
    return proc.stdout.strip()


def _git(args: list[str], cwd: Path) -> str:
    return _require_ok(_run(["git", *args], cwd=cwd), f"git {' '.join(args)}")


def _parse_upstream_provenance(text: str) -> dict:
    repository = ""
    sha = ""
    patches: list[str] = []
    in_patches = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("repo:"):
            repository = line.split(":", 1)[1].strip()
        elif line.startswith("sha:"):
            sha = line.split(":", 1)[1].strip()
        elif line.startswith("patches:"):
            in_patches = True
        elif in_patches:
            if not line:
                in_patches = False
            elif line.startswith("patches/") and line.endswith(".patch"):
                patches.append(line)
            else:
                in_patches = False
    return {"repository": repository, "sha": sha, "patches": patches}


def _header_version(source_dir: Path) -> str:
    header = source_dir / "include" / "transcribe.h"
    try:
        text = header.read_text(encoding="utf-8")
    except OSError as exc:
        raise BuildError(f"cannot read public version header {header}: {exc}") from exc
    values = {}
    for name in ("MAJOR", "MINOR", "PATCH"):
        marker = f"#define TRANSCRIBE_VERSION_{name} "
        for line in text.splitlines():
            if line.startswith(marker):
                values[name] = line[len(marker) :].strip()
                break
        else:
            raise BuildError(f"missing TRANSCRIBE_VERSION_{name} in {header}")
    return f"{values['MAJOR']}.{values['MINOR']}.{values['PATCH']}"


def _binding_version(source_dir: Path) -> str:
    init = source_dir / "bindings" / "python" / "src" / "transcribe_cpp" / "__init__.py"
    try:
        text = init.read_text(encoding="utf-8")
    except OSError as exc:
        raise BuildError(f"cannot read Python binding version {init}: {exc}") from exc
    for line in text.splitlines():
        if line.startswith("__version__ = "):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise BuildError(f"missing __version__ in {init}")


def verify_checkout(
    source_dir: Path = SOURCE_DIR,
    *,
    expected_revision: str = ENGINE_REVISION,
    expected_version: str = ENGINE_VERSION,
    expected_ggml_sha: str = EXPECTED_GGML_UPSTREAM_SHA,
    expected_ggml_tree: str = EXPECTED_GGML_TREE,
    expected_patch_tree: str = EXPECTED_PATCH_TREE,
    require_clean: bool = True,
    verify_remote: bool = True,
) -> dict:
    """Verify the pinned source checkout and return its provenance.

    Fails closed on a wrong revision, a dirty tree, a mutated vendored ggml tree
    or patch set, a non-empty submodule set, or a version mismatch.  This is the
    tamper guard exercised by the unit tests.
    """
    source_dir = Path(source_dir)
    if not (source_dir / ".git").exists():
        raise BuildError(f"not a git checkout: {source_dir}")

    head = _git(["rev-parse", "HEAD"], source_dir)
    if head != expected_revision:
        raise BuildError(
            f"engine revision mismatch: expected {expected_revision}, found {head}"
        )

    if verify_remote:
        remote = _git(["remote", "get-url", "origin"], source_dir)
        normalized = remote.removesuffix(".git")
        if normalized != ENGINE_REPOSITORY:
            raise BuildError(
                f"engine origin mismatch: expected {ENGINE_REPOSITORY}, found {remote}"
            )

    if require_clean:
        status = _git(["status", "--porcelain"], source_dir)
        if status:
            raise BuildError(
                "engine source tree is dirty; refusing to build or verify a "
                f"modified pin:\n{status}"
            )

    if (source_dir / ".gitmodules").exists():
        raise BuildError("unexpected .gitmodules in pinned engine checkout")
    submodules = _git(["submodule", "status"], source_dir)
    if submodules:
        raise BuildError(f"unexpected submodules in pinned engine checkout:\n{submodules}")

    version = _header_version(source_dir)
    if version != expected_version:
        raise BuildError(
            f"engine version mismatch: expected {expected_version}, header says {version}"
        )
    binding_version = _binding_version(source_dir)
    if binding_version != expected_version:
        raise BuildError(
            "Python binding version mismatch: expected "
            f"{expected_version}, binding says {binding_version}"
        )

    upstream_path = source_dir / "ggml" / "UPSTREAM"
    try:
        upstream_text = upstream_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BuildError(f"missing vendored ggml provenance {upstream_path}: {exc}") from exc
    upstream = _parse_upstream_provenance(upstream_text)
    if upstream["repository"] != EXPECTED_GGML_UPSTREAM_REPOSITORY:
        raise BuildError(
            "vendored ggml repository mismatch: expected "
            f"{EXPECTED_GGML_UPSTREAM_REPOSITORY}, found {upstream['repository']!r}"
        )
    if upstream["sha"] != expected_ggml_sha:
        raise BuildError(
            f"vendored ggml sha mismatch: expected {expected_ggml_sha}, "
            f"UPSTREAM says {upstream['sha']}"
        )
    ggml_tree = _git(["rev-parse", "HEAD:ggml"], source_dir)
    if ggml_tree != expected_ggml_tree:
        raise BuildError(
            f"vendored ggml tree mismatch: expected {expected_ggml_tree}, found {ggml_tree}"
        )
    patch_tree = _git(["rev-parse", "HEAD:patches"], source_dir)
    if patch_tree != expected_patch_tree:
        raise BuildError(
            f"patch tree mismatch: expected {expected_patch_tree}, found {patch_tree}"
        )

    abi_path = source_dir / "include" / "transcribe.abihash"
    try:
        abi_hash = abi_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise BuildError(f"missing ABI hash file {abi_path}: {exc}") from exc
    if abi_hash != EXPECTED_ABI_HASH:
        raise BuildError(
            f"ABI hash mismatch: expected {EXPECTED_ABI_HASH}, found {abi_hash!r}"
        )

    patch_files = []
    for patch in upstream["patches"]:
        patch_path = source_dir / patch
        if not patch_path.is_file():
            raise BuildError(f"vendored ggml patch listed in UPSTREAM is missing: {patch}")
        patch_files.append(
            {"path": patch, "sha256": sha256_file(patch_path)}
        )

    return {
        "repository": ENGINE_REPOSITORY,
        "revision": head,
        "version": version,
        "python_binding_version": binding_version,
        "python_binding_path": "bindings/python",
        "abi_hash": abi_hash,
        "abi_hash_file_sha256": sha256_file(abi_path),
        "clean_tree_verified": bool(require_clean),
        "submodules": [],
        "ggml": {
            "upstream_repository": upstream["repository"],
            "upstream_sha": upstream["sha"],
            "vendored_tree": ggml_tree,
            "patch_tree": patch_tree,
            "patches": patch_files,
            "upstream_file": "ggml/UPSTREAM",
        },
    }


def ensure_checkout(
    *,
    source_dir: Path = SOURCE_DIR,
    revision: str = ENGINE_REVISION,
    repository: str = ENGINE_REPOSITORY,
) -> None:
    """Clone or fetch the exact pinned revision into the ignored tools tree."""
    source_dir = Path(source_dir)
    source_dir.parent.mkdir(parents=True, exist_ok=True)

    if not (source_dir / ".git").exists():
        if source_dir.exists() and any(source_dir.iterdir()):
            raise BuildError(
                f"{source_dir} exists but is not a git checkout; remove it explicitly"
            )
        print(f"clone: {repository} @ {revision}", flush=True)
        _require_ok(_run(["git", "init", "-q", str(source_dir)]), "git init")
        _git(["remote", "add", "origin", repository], source_dir)

    remote = _git(["remote", "get-url", "origin"], source_dir)
    normalized = remote.removesuffix(".git")
    if normalized != repository:
        raise BuildError(
            f"existing checkout has origin {remote!r}, expected {repository!r}"
        )

    try:
        head = _git(["rev-parse", "HEAD"], source_dir)
    except BuildError:
        head = ""
    if head != revision:
        print(f"fetch: {revision}", flush=True)
        _require_ok(
            _run(["git", "fetch", "--depth", "1", "origin", revision], cwd=source_dir),
            f"git fetch {revision}",
        )
        _git(["checkout", "-q", "--detach", "FETCH_HEAD"], source_dir)

    head = _git(["rev-parse", "HEAD"], source_dir)
    if head != revision:
        raise BuildError(f"checkout did not land on {revision}; found {head}")


def _cmake_executable() -> str:
    found = shutil.which("cmake")
    if not found:
        raise BuildError("cmake is not on PATH")
    return found


def _generator_args() -> list[str]:
    if shutil.which("ninja"):
        return ["-G", "Ninja"]
    return []


def _parallel_jobs(requested: int | None) -> int:
    if requested is not None:
        if requested < 1:
            raise BuildError("--jobs must be a positive integer")
        return requested
    return max(1, min(os.cpu_count() or 4, 8))


def build(
    *,
    source_dir: Path = SOURCE_DIR,
    build_dir: Path = BUILD_DIR,
    jobs: int | None = None,
    clean: bool = False,
    reconfigure: bool = False,
) -> Path:
    """Configure and build the shared library; return its path."""
    source_dir = Path(source_dir)
    build_dir = Path(build_dir)
    cmake = _cmake_executable()

    if clean and build_dir.exists():
        print(f"clean: removing {build_dir}", flush=True)
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True, exist_ok=True)

    cache = build_dir / "CMakeCache.txt"
    if reconfigure and cache.exists():
        cache.unlink()

    configure = [
        cmake,
        "-S",
        str(source_dir),
        "-B",
        str(build_dir),
        *_generator_args(),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DTRANSCRIBE_BUILD_SHARED=ON",
        "-DTRANSCRIBE_BUILD_TESTS=OFF",
        "-DTRANSCRIBE_BUILD_EXAMPLES=OFF",
        "-DTRANSCRIBE_BUILD_TOOLS=OFF",
        "-DTRANSCRIBE_METAL=ON",
        "-DGGML_METAL=ON",
        "-DGGML_METAL_EMBED_LIBRARY=ON",
        "-DTRANSCRIBE_USE_OPENMP=OFF",
        "-DGGML_NATIVE=ON",
    ]
    print("configure:", shlex.join(configure), flush=True)
    _require_ok(_run(configure, cwd=source_dir), "cmake configure")

    jobs = _parallel_jobs(jobs)
    build_cmd = [cmake, "--build", str(build_dir), "--config", "Release", "--parallel", str(jobs)]
    print("build:", shlex.join(build_cmd), flush=True)
    _require_ok(_run(build_cmd, cwd=source_dir), "cmake build")

    library = find_library(build_dir)
    if library is None:
        raise BuildError(f"build finished but no shared library was found under {build_dir}")
    return library


def find_library(build_dir: Path = BUILD_DIR) -> Path | None:
    build_dir = Path(build_dir)
    name = _library_filename()
    for candidate in (
        build_dir / "bin" / name,
        build_dir / "src" / name,
        build_dir / "lib" / name,
        build_dir / name,
    ):
        if candidate.is_file():
            return candidate
    return None


def _cache_value(cache_path: Path, key: str) -> str | None:
    if not cache_path.is_file():
        return None
    prefix = f"{key}:"
    for line in cache_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1] if "=" in line else ""
    return None


def _tool_version(args: list[str]) -> str | None:
    try:
        proc = _run(args, timeout=30)
    except BuildError:
        return None
    if proc.returncode != 0:
        return None
    first = (proc.stdout or proc.stderr).strip().splitlines()
    return first[0].strip() if first else None


def import_check(library: Path, binding_src: Path = BINDING_SRC) -> dict:
    """Load the native library through the official binding; no model is used."""
    library = Path(library).resolve()
    binding_src = Path(binding_src).resolve()
    if not (binding_src / "transcribe_cpp" / "__init__.py").is_file():
        return {"ok": False, "error": f"binding source missing under {binding_src}"}
    env = dict(os.environ)
    env["TRANSCRIBE_LIBRARY"] = str(library)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    script = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
sys.dont_write_bytecode = True
import transcribe_cpp
out = {
    "ok": True,
    "module_version": transcribe_cpp.__version__,
    "native_version": transcribe_cpp.native_version(),
    "native_commit": transcribe_cpp.native_commit(),
    "library_path": transcribe_cpp.library_path(),
    "backends": [
        {
            "name": d.name,
            "kind": d.kind,
            "device_type": d.device_type,
            "device_id": d.device_id,
            "memory_total": d.memory_total,
        }
        for d in transcribe_cpp.backends()
    ],
}
print(json.dumps(out, allow_nan=False))
"""
    proc = _run([sys.executable, "-c", script, str(binding_src)], env=env, timeout=180)
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": (proc.stderr or proc.stdout or "").strip()[-4000:],
        }
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        return {"ok": False, "error": f"could not parse import-check output: {exc}"}
    payload["stderr"] = (proc.stderr or "").strip()[-4000:] or None
    return payload


def verify_artifact_against_lock(library: Path, lock_path: Path = LOCK_PATH) -> dict:
    """Fail when the built artifact or source pin disagrees with the lock."""
    lock_path = Path(lock_path)
    if not lock_path.is_file():
        return {"lock_present": False, "verified": False}
    try:
        with open(lock_path, "r", encoding="utf-8") as handle:
            lock = json.load(handle)
    except (OSError, ValueError) as exc:
        raise BuildError(f"cannot read {lock_path}: {exc}") from exc
    if lock.get("schema_version") != 1:
        raise BuildError(f"unsupported engine lock schema in {lock_path}")
    try:
        expected = lock["artifact"]["sha256"]
        expected_path = lock["artifact"]["path"]
        expected_revision = lock["engine"]["revision"]
        expected_version = lock["engine"]["version"]
    except (KeyError, TypeError) as exc:
        raise BuildError(f"engine lock {lock_path} is missing {exc}") from exc

    library = Path(library).resolve()
    actual = sha256_file(library)
    expected_abs = (SPIKE_ROOT / expected_path).resolve()
    if expected_abs != library:
        raise BuildError(
            f"built artifact {library} does not match locked path {expected_path}"
        )
    if actual != expected:
        raise BuildError(
            "artifact hash mismatch after build: lock records "
            f"{expected}, artifact is {actual}. Review and update engine.lock.json."
        )
    return {
        "lock_present": True,
        "verified": True,
        "path": expected_path,
        "sha256": actual,
        "engine_revision": expected_revision,
        "engine_version": expected_version,
    }


def verify_lock_source_pin(source_verification: dict, lock_path: Path = LOCK_PATH) -> None:
    """Cross-check build-script constants against the reviewed lock record."""
    lock_path = Path(lock_path)
    if not lock_path.is_file():
        raise BuildError(f"engine lock is missing: {lock_path}")
    try:
        with open(lock_path, "r", encoding="utf-8") as handle:
            lock = json.load(handle)
    except (OSError, ValueError) as exc:
        raise BuildError(f"cannot read {lock_path}: {exc}") from exc
    engine = lock.get("engine") or {}
    source = lock.get("source_verification") or {}
    ggml = source.get("ggml") or {}
    checks = {
        "engine.repository": (engine.get("repository"), source_verification["repository"]),
        "engine.revision": (engine.get("revision"), source_verification["revision"]),
        "engine.version": (engine.get("version"), source_verification["version"]),
        "engine.abi_hash": (engine.get("abi_hash"), source_verification["abi_hash"]),
        "engine.python_binding_version": (
            (engine.get("python_binding") or {}).get("version"),
            source_verification["python_binding_version"],
        ),
        "ggml.upstream_repository": (
            ggml.get("upstream_repository"),
            source_verification["ggml"]["upstream_repository"],
        ),
        "ggml.upstream_sha": (
            ggml.get("upstream_sha"),
            source_verification["ggml"]["upstream_sha"],
        ),
        "ggml.vendored_tree": (
            ggml.get("vendored_tree"),
            source_verification["ggml"]["vendored_tree"],
        ),
        "ggml.patch_tree": (
            ggml.get("patch_tree"),
            source_verification["ggml"]["patch_tree"],
        ),
    }
    mismatches = [
        f"{name}: lock={locked!r}, checkout={actual!r}"
        for name, (locked, actual) in checks.items()
        if locked != actual
    ]
    if mismatches:
        raise BuildError("engine lock/source drift:\n" + "\n".join(mismatches))


def build_metadata(
    *,
    source_verification: dict,
    library: Path,
    build_dir: Path = BUILD_DIR,
    import_result: dict | None = None,
) -> dict:
    library = Path(library)
    build_dir = Path(build_dir)
    cache = build_dir / "CMakeCache.txt"
    configure_keys = (
        "CMAKE_BUILD_TYPE",
        "CMAKE_CXX_COMPILER",
        "CMAKE_GENERATOR",
        "TRANSCRIBE_BUILD_SHARED",
        "TRANSCRIBE_BUILD_TESTS",
        "TRANSCRIBE_BUILD_EXAMPLES",
        "TRANSCRIBE_BUILD_TOOLS",
        "TRANSCRIBE_METAL",
        "GGML_METAL",
        "GGML_METAL_EMBED_LIBRARY",
        "TRANSCRIBE_USE_OPENMP",
        "GGML_NATIVE",
        "TRANSCRIBE_BUILD_COMMIT",
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source_verification,
        "build": {
            "command": "python3 spikes/001-transcription/tools/build_engine.py",
            "build_dir": ".tools/build",
            "artifact_relative_path": library.relative_to(SPIKE_ROOT).as_posix()
            if library.is_relative_to(SPIKE_ROOT)
            else str(library),
            "cmake": _tool_version(["cmake", "--version"]),
            "generator": _tool_version(["ninja", "--version"]),
            "compiler": _tool_version(["c++", "--version"]),
            "xcode_select": _tool_version(["xcode-select", "-p"]),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "cache": {key: _cache_value(cache, key) for key in configure_keys},
        },
        "artifact": {
            "path": str(library.relative_to(SPIKE_ROOT).as_posix())
            if library.is_relative_to(SPIKE_ROOT)
            else str(library),
            "sha256": sha256_file(library),
            "size_bytes": library.stat().st_size,
        },
        "import_check": import_result,
    }


def write_json_atomic(path: Path, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="verify the pinned checkout/artifact without configuring or building",
    )
    parser.add_argument(
        "--import-check",
        action="store_true",
        help="load the built library through the official Python binding (no model)",
    )
    parser.add_argument("--clean", action="store_true", help="remove the build directory first")
    parser.add_argument("--reconfigure", action="store_true", help="discard the CMake cache")
    parser.add_argument("--jobs", type=int, default=None, help="parallel build jobs")
    parser.add_argument(
        "--no-clean-required",
        action="store_true",
        help="allow a dirty source tree (for local debugging only; recorded as unverified)",
    )
    args = parser.parse_args(argv)

    try:
        ensure_checkout()
        verification = verify_checkout(require_clean=not args.no_clean_required)
        verify_lock_source_pin(verification)
        print(
            "pin verified:",
            verification["revision"],
            "version",
            verification["version"],
            "ggml",
            verification["ggml"]["upstream_sha"],
            flush=True,
        )

        library = find_library()
        if args.verify_only:
            if library is None:
                raise BuildError("no built library; run without --verify-only first")
            lock_check = verify_artifact_against_lock(library)
            payload = build_metadata(
                source_verification=verification,
                library=library,
                import_result=None,
            )
            payload["lock_check"] = lock_check
            print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
            return 0

        library = build(jobs=args.jobs, clean=args.clean, reconfigure=args.reconfigure)
        verification = verify_checkout(require_clean=not args.no_clean_required)
        lock_check = verify_artifact_against_lock(library)
        import_result = None
        if args.import_check:
            import_result = import_check(library)
            if not import_result.get("ok"):
                raise BuildError(f"binding import check failed: {import_result.get('error')}")
        payload = build_metadata(
            source_verification=verification,
            library=library,
            import_result=import_result,
        )
        payload["lock_check"] = lock_check
        write_json_atomic(BUILD_METADATA_PATH, payload)
        print(
            json.dumps(
                {
                    "artifact": payload["artifact"],
                    "import_check": import_result,
                    "metadata": str(BUILD_METADATA_PATH.relative_to(SPIKE_ROOT)),
                },
                indent=2,
                sort_keys=True,
                allow_nan=False,
            ),
            flush=True,
        )
        return 0
    except BuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
