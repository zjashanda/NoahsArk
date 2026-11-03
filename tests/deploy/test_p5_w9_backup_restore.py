"""P5-W9 local backup, checksum and non-destructive restore checks.

PostgreSQL is replaced by fake ``pg_dump``/``pg_restore`` executables. These
tests prove script mechanics only: no database, RPO/RTO, off-host durability
or production recovery is exercised or claimed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from conftest import SCRIPTS, base_env, run, with_path

BACKUP = SCRIPTS / "backup.sh"
RESTORE = SCRIPTS / "restore-drill.sh"


def _snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "<dir>"
        )
        for path in sorted(root.rglob("*"))
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_backup_dry_run_writes_nothing(tmp_path: Path):
    # Given a destination and evidence root that do not exist yet
    dest = tmp_path / "backups"
    evidence = tmp_path / "evidence"
    env = base_env(NAA_BACKUP_DIR=str(dest), NAA_EVIDENCE_ROOT=str(evidence))

    # When backup runs in its default dry-run mode
    result = run([str(BACKUP), "--dry-run"], env=env)

    # Then it plans the work but creates no file or directory anywhere
    assert result.returncode == 0, result.stderr
    assert "dry-run: no files written, nothing deleted" in result.stdout
    assert not dest.exists()
    assert not evidence.exists()
    assert sorted(tmp_path.iterdir()) == []


def test_backup_execute_writes_a_checksummed_manifest(backup_factory, tmp_path: Path):
    # Given existing database/evidence inputs
    # When an executed backup completes
    backup_dir = backup_factory(tmp_path / "case")

    # Then every artifact exists, is owner-only, and matches SHA256SUMS
    for name in ("db.dump", "evidence.tar.gz", "manifest.json", "SHA256SUMS"):
        assert (backup_dir / name).is_file(), name
    assert oct(backup_dir.stat().st_mode & 0o777) == "0o700"
    checksums = run(["sha256sum", "-c", "SHA256SUMS"], cwd=backup_dir)
    assert checksums.returncode == 0, checksums.stderr
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["database"]["sha256"] == _sha256(backup_dir / "db.dump")
    assert manifest["evidence"]["sha256"] == _sha256(backup_dir / "evidence.tar.gz")
    assert "PGDMP fake custom-format dump" in (backup_dir / "db.dump").read_text(encoding="utf-8")


def test_restore_dry_run_verifies_checksums_without_writing(backup_factory, tmp_path: Path, fake_pg: Path):
    # Given a valid backup
    backup_dir = backup_factory(tmp_path / "case")
    before = _snapshot(backup_dir)
    planned_evidence = backup_dir / "restored-evidence-drill"

    # When the restore drill runs in dry-run mode
    result = run([str(RESTORE), "--backup-dir", str(backup_dir)], env=with_path(fake_pg))

    # Then checksums pass and nothing on disk changes
    assert result.returncode == 0, result.stderr
    assert "checksums          : OK" in result.stdout
    assert "no database or directory was modified" in result.stdout
    assert not planned_evidence.exists()
    assert _snapshot(backup_dir) == before


@pytest.mark.parametrize("tampered", ["db.dump", "manifest.json"])
def test_restore_dry_run_rejects_a_tampered_backup(backup_factory, tmp_path: Path, fake_pg: Path, tampered: str):
    # Given a backup whose covered artifact changed after checksumming
    backup_dir = backup_factory(tmp_path / "case")
    with (backup_dir / tampered).open("ab") as handle:
        handle.write(b"tamper\n")

    # When the restore drill verifies it
    result = run([str(RESTORE), "--backup-dir", str(backup_dir)], env=with_path(fake_pg))

    # Then it fails closed before touching any target
    assert result.returncode == 3
    assert "checksum verification failed" in result.stderr
    assert not (backup_dir / "restored-evidence-drill").exists()


def test_restore_execute_requires_confirmation(backup_factory, tmp_path: Path, fake_pg: Path):
    # Given a valid backup and drill DSN but no --confirm
    backup_dir = backup_factory(tmp_path / "case")
    log = tmp_path / "pg_restore.log"
    env = with_path(fake_pg)
    env.update(
        {
            "NAA_RESTORE_DSN": "postgresql://noahsark:PLACEHOLDER@127.0.0.1:5432/noahsark_drill",
            "FAKE_PG_RESTORE_LOG": str(log),
        }
    )

    # When --execute is requested without confirmation
    result = run(
        [str(RESTORE), "--backup-dir", str(backup_dir), "--target-db", "noahsark_drill", "--execute"],
        env=env,
    )

    # Then it refuses before invoking pg_restore
    assert result.returncode == 1
    assert "--execute requires --confirm" in result.stderr
    assert not log.exists()


def test_restore_execute_rejects_a_non_drill_target(backup_factory, tmp_path: Path, fake_pg: Path):
    # Given a confirmed restore pointed at a non-drill database name
    backup_dir = backup_factory(tmp_path / "case")
    log = tmp_path / "pg_restore.log"
    env = with_path(fake_pg)
    env.update(
        {
            "NAA_RESTORE_DSN": "postgresql://noahsark:PLACEHOLDER@127.0.0.1:5432/noahsark",
            "FAKE_PG_RESTORE_LOG": str(log),
        }
    )

    # When the drill runs
    result = run(
        [str(RESTORE), "--backup-dir", str(backup_dir), "--target-db", "noahsark", "--execute", "--confirm"],
        env=env,
    )

    # Then the non-drill target is rejected and nothing is restored
    assert result.returncode == 1
    assert "must end in _drill" in result.stderr
    assert not log.exists()


def test_restore_execute_rejects_the_configured_source_database(backup_factory, tmp_path: Path, fake_pg: Path):
    # Given DATABASE_URL naming the same drill-suffixed database as the target
    backup_dir = backup_factory(tmp_path / "case")
    env = with_path(fake_pg)
    env.update(
        {
            "DATABASE_URL": "postgresql+asyncpg://noahsark:PLACEHOLDER@127.0.0.1:5432/noahsark_drill",
            "NAA_RESTORE_DSN": "postgresql://noahsark:PLACEHOLDER@127.0.0.1:5432/noahsark_drill",
        }
    )

    # When the drill runs
    result = run(
        [str(RESTORE), "--backup-dir", str(backup_dir), "--target-db", "noahsark_drill", "--execute", "--confirm"],
        env=env,
    )

    # Then it refuses to overwrite the source database
    assert result.returncode == 1
    assert "equals the configured source database" in result.stderr


def test_restore_execute_refuses_a_non_empty_evidence_target(backup_factory, tmp_path: Path, fake_pg: Path):
    # Given a pre-populated evidence target
    backup_dir = backup_factory(tmp_path / "case")
    target = tmp_path / "occupied"
    target.mkdir()
    (target / "keep.txt").write_text("do not overwrite\n", encoding="utf-8")
    log = tmp_path / "pg_restore.log"
    env = with_path(fake_pg)
    env.update(
        {
            "NAA_RESTORE_DSN": "postgresql://noahsark:PLACEHOLDER@127.0.0.1:5432/noahsark_drill",
            "FAKE_PG_RESTORE_LOG": str(log),
        }
    )

    # When the drill runs against it
    result = run(
        [
            str(RESTORE),
            "--backup-dir",
            str(backup_dir),
            "--target-db",
            "noahsark_drill",
            "--evidence-target",
            str(target),
            "--execute",
            "--confirm",
        ],
        env=env,
    )

    # Then it refuses before restoring and leaves the existing file alone
    assert result.returncode == 1
    assert "not empty, refusing to overwrite" in result.stderr
    assert not log.exists()
    assert (target / "keep.txt").read_text(encoding="utf-8") == "do not overwrite\n"


def test_restore_execute_extracts_into_an_empty_drill_target(backup_factory, tmp_path: Path, fake_pg: Path):
    # Given an empty drill target and a valid backup
    backup_dir = backup_factory(tmp_path / "case")
    target = tmp_path / "drill-evidence"
    log = tmp_path / "pg_restore.log"
    env = with_path(fake_pg)
    env.update(
        {
            "NAA_RESTORE_DSN": "postgresql://noahsark:PLACEHOLDER@127.0.0.1:5432/noahsark_drill",
            "FAKE_PG_RESTORE_LOG": str(log),
        }
    )

    # When the confirmed drill executes
    result = run(
        [
            str(RESTORE),
            "--backup-dir",
            str(backup_dir),
            "--target-db",
            "noahsark_drill",
            "--evidence-target",
            str(target),
            "--execute",
            "--confirm",
        ],
        env=env,
    )

    # Then the fake restore is invoked and evidence lands only in the target
    assert result.returncode == 0, result.stderr
    assert "restore-drill: complete" in result.stdout
    invocation = log.read_text(encoding="utf-8")
    assert "--clean --if-exists" in invocation
    assert "--dbname=postgresql://noahsark:PLACEHOLDER@127.0.0.1:5432/noahsark_drill" in invocation
    assert (target / "evidence" / "sample.json").is_file()
