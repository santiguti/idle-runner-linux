"""packaging/install.sh ships in the Linux release: it copies the extracted folder under ~/.local/share and
adds a menu entry. Tested against a fake package, with a $HOME that has a space in it."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ICON = "_internal/idle_runner/ui/assets/icon.png"

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="install.sh is for Linux")


@pytest.fixture
def pkg(tmp_path: Path) -> Path:
    folder = tmp_path / "pkg dir"
    (folder / ICON).parent.mkdir(parents=True)
    (folder / ICON).write_bytes(b"png")
    (folder / "IdleRunner").write_text("#!/bin/sh\n")
    (folder / "IdleRunner").chmod(0o755)
    shutil.copy(ROOT / "packaging" / "install.sh", folder / "install.sh")
    return folder


@pytest.fixture
def home(tmp_path: Path) -> Path:
    return tmp_path / "my home"


def install(pkg: Path, home: Path) -> subprocess.CompletedProcess[str]:
    env = {"HOME": str(home), "PATH": os.environ["PATH"]}
    return subprocess.run(["bash", str(pkg / "install.sh")], env=env, capture_output=True, text=True, check=True)


def test_it_installs_and_adds_a_menu_entry(pkg: Path, home: Path) -> None:
    result = install(pkg, home)

    dest = home / ".local/share/idle-runner"
    assert (dest / "IdleRunner").is_file() and os.access(dest / "IdleRunner", os.X_OK)
    desktop = (home / ".local/share/applications/idle-runner.desktop").read_text()
    assert f'Exec="{dest}/IdleRunner"' in desktop
    assert f"Icon={dest}/{ICON}" in desktop
    for line in ("Type=Application", "Name=Idle Runner", "Terminal=false", "Categories=Game;"):
        assert line in desktop
    assert str(dest) in result.stdout


def test_reinstalling_keeps_the_config_and_logs(pkg: Path, home: Path) -> None:
    install(pkg, home)
    dest = home / ".local/share/idle-runner"
    (dest / "config.toml").write_text("mine")
    (dest / "logs").mkdir()
    (dest / "logs/events.jsonl").write_text("x")

    install(pkg, home)

    assert (dest / "config.toml").read_text() == "mine"
    assert (dest / "logs/events.jsonl").read_text() == "x"
