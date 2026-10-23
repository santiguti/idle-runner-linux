import json
from collections.abc import Callable
from pathlib import Path

import pytest

from idle_runner.game import Game
from idle_runner.log import setup_logging
from tests.fakes import OFFSET, FakeBackend, FakeJumper


@pytest.fixture(autouse=True)
def logs(tmp_path: Path) -> Path:
    """Every test logs (at DEBUG) into its own temporary directory."""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir, "DEBUG")
    return log_dir


@pytest.fixture
def events(logs: Path) -> Callable[[], list[dict]]:
    """Read back the events.jsonl records written so far."""
    def read() -> list[dict]:
        path = logs / "events.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    return read


@pytest.fixture
def event_names(events: Callable[[], list[dict]]) -> Callable[[], list[str]]:
    return lambda: [record["event"] for record in events()]


@pytest.fixture
def fake() -> FakeBackend:
    return FakeBackend()


@pytest.fixture
def game(fake: FakeBackend, tmp_path: Path) -> Game:
    return Game(fake, offset=OFFSET, frames_dir=tmp_path / "frames")


@pytest.fixture
def jumper() -> FakeJumper:
    return FakeJumper()
