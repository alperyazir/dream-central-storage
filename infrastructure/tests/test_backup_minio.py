from __future__ import annotations

import json
from pathlib import Path
from typing import List
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from infrastructure.scripts.backup_minio import (
    BackupConfig,
    BackupError,
    run_backup,
)


class StubRunner:
    def __init__(self) -> None:
        self.commands: List[List[str]] = []
        self.outputs: dict[str, str] = {}

    def add_output(self, startswith: str, stdout: str) -> None:
        self.outputs[startswith] = stdout

    def __call__(self, command: List[str]):
        self.commands.append(command)
        key = " ".join(command[:3])
        stdout = ""
        for prefix, output in self.outputs.items():
            if " ".join(command).startswith(prefix):
                stdout = output
                break
        return Completed(stdout)


class Completed:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.stderr = ""


@pytest.fixture()
def config(tmp_path: Path) -> BackupConfig:
    return BackupConfig(
        mc_path="mc",
        source_endpoint="https://source",
        source_access_key="source-key",
        source_secret_key="source-secret",
        backup_endpoint="https://backup",
        backup_access_key="backup-key",
        backup_secret_key="backup-secret",
        backup_bucket="dream",
        buckets=("books", "apps"),
        log_path=tmp_path / "backup.log",
    )


def test_run_backup_invokes_alias_bucket_and_mirror(config: BackupConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = StubRunner()
    runner.add_output("mc mirror", json.dumps({"status": "success"}))

    # Configure logging to use a null handler during test execution.
    monkeypatch.setattr("infrastructure.scripts.backup_minio._configure_logging", lambda path: None)

    run_backup(config, runner=runner)

    commands = runner.commands
    assert commands[0][:4] == ["mc", "alias", "set", "source"]
    assert commands[1][:4] == ["mc", "alias", "set", "backup"]
    assert ["mc", "mb", "--ignore-existing", "backup/dream"] in commands
    assert ["mc", "mb", "--ignore-existing", "backup/dream/books"] in commands
    assert ["mc", "mb", "--ignore-existing", "backup/dream/apps"] in commands
    mirror_commands = [cmd for cmd in commands if cmd[1] == "mirror"]
    assert ["mc", "mirror", "--json", "--overwrite", "--remove", "source/books", "backup/dream/books"] in mirror_commands


def test_run_backup_raises_on_mirror_failure(config: BackupConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_runner(command):
        if command[1] == "mirror":
            raise subprocess.CalledProcessError(1, command, stderr="boom")
        return Completed("")

    monkeypatch.setattr("infrastructure.scripts.backup_minio._configure_logging", lambda path: None)

    with pytest.raises(BackupError):
        run_backup(config, runner=failing_runner)
