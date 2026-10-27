"""The release workflow only runs on GitHub (a pushed v2+ tag, on Windows). What can break it from here is a
file it uses being moved or a build dependency dropped, so that is what these check."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")


def test_the_build_extra_has_pyinstaller_and_pillow() -> None:
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"]

    assert {"pyinstaller", "pillow"} <= {name.split(">")[0].strip().lower() for name in extras["build"]}


def test_the_files_it_uses_exist() -> None:
    for name in ("packaging/entry.py", "packaging/README.txt", "config.example.toml", "LICENSE", "CHANGELOG.md"):
        assert name in WORKFLOW, name
        assert (ROOT / name).is_file(), name
