"""Rebuild or verify the texture-v1 audit artifact from its Git revision.

This audit tool extracts the immutable source revision into a temporary
directory, overlays only the shared scenario harness, and executes that
revision with the current Python interpreter.  It never checks out files in
the working tree and never accesses a database or network service.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from app.services.texture_profile_report import (
    BASELINE_GENERATION_CONTRACT,
    BASELINE_PATH,
    BASELINE_SCHEMA_VERSION,
    COMPARISON_MONTH,
    COMPARISON_RANDOM_SEED,
    COMPARISON_SCOPE,
    COMPARISON_TODAY,
    ROOT,
    V1_SOURCE_REVISION,
)


def _run(
    *args: str,
    cwd: Path,
    text: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=text,
    )


def _safe_extract(archive_path: Path, destination: Path) -> None:
    with zipfile.ZipFile(archive_path) as archive:
        for name in archive.namelist():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError(f"unsafe path in Git archive: {name}")
        archive.extractall(destination)


def replay_v1_source_revision() -> dict[str, object]:
    resolved = _run(
        "git",
        "rev-parse",
        V1_SOURCE_REVISION,
        cwd=ROOT,
    ).stdout.strip()
    if resolved != V1_SOURCE_REVISION:
        raise RuntimeError("configured v1 source revision does not resolve exactly")

    with tempfile.TemporaryDirectory(prefix="daily-fruit-v1-replay-") as raw_temp:
        temp = Path(raw_temp)
        archive_path = temp / "source.zip"
        archive = _run(
            "git",
            "archive",
            "--format=zip",
            V1_SOURCE_REVISION,
            cwd=ROOT,
            text=False,
        ).stdout
        archive_path.write_bytes(archive)
        source = temp / "source"
        source.mkdir()
        _safe_extract(archive_path, source)

        harness_target = source / "backend/app/services/texture_profile_report.py"
        harness_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            ROOT / "backend/app/services/texture_profile_report.py",
            harness_target,
        )

        runner = (
            "import json; "
            "from app.services.texture_profile_report import _version_snapshot; "
            "print(json.dumps(_version_snapshot(use_legacy_users=True), "
            "ensure_ascii=False, sort_keys=True))"
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(source / "backend")
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-c", runner],
            cwd=source / "backend",
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(
                "v1 source-revision replay failed:\n" + result.stderr.strip()
            )
        profiles = json.loads(result.stdout)

    return {
        "schema_version": BASELINE_SCHEMA_VERSION,
        "source_revision": V1_SOURCE_REVISION,
        "source_scoring_model": "taste-v1",
        "generation_contract": BASELINE_GENERATION_CONTRACT,
        "comparison_scope": COMPARISON_SCOPE,
        "comparison_context": {
            "today": COMPARISON_TODAY.isoformat(),
            "month": COMPARISON_MONTH,
            "random_seed": COMPARISON_RANDOM_SEED,
        },
        "profiles": profiles,
    }


def _serialize(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def verify_checked_in_baseline() -> None:
    expected = replay_v1_source_revision()
    actual = BASELINE_PATH.read_text(encoding="utf-8")
    if actual != _serialize(expected):
        raise RuntimeError(
            "checked-in v1 baseline is not the canonical source-revision replay"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--verify", action="store_true")
    action.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if args.verify:
        verify_checked_in_baseline()
        print(f"verified {V1_SOURCE_REVISION}")
        return 0
    payload = replay_v1_source_revision()
    BASELINE_PATH.write_text(_serialize(payload), encoding="utf-8")
    print(BASELINE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
