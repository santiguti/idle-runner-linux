"""The release workflow only runs on GitHub (a pushed v2+ tag, on Windows and Linux). What can break it from here is a
file it uses being moved or a build dependency dropped, so that is what these check."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")


def test_the_build_extra_has_pyinstaller_and_pillow() -> None:
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["optional-dependencies"]

    assert {"pyinstaller", "pillow"} <= {name.split(">")[0].strip().lower() for name in extras["build"]}


def test_the_files_it_uses_exist() -> None:
    for name in ("packaging/entry.py", "packaging/README.txt", "packaging/README-linux.txt", "packaging/install.sh","config.example.toml", "LICENSE", "CHANGELOG.md"):
        assert name in WORKFLOW, name
        assert (ROOT / name).is_file(), name


def test_it_builds_windows_and_linux() -> None:
    assert "windows-latest" in WORKFLOW and "ubuntu-22.04" in WORKFLOW


def test_it_publishes_only_after_every_build_and_only_on_tags() -> None:
    assert "needs: build" in WORKFLOW
    assert "startsWith(github.ref, 'refs/tags/')" in WORKFLOW


def test_it_can_be_run_by_hand_without_a_tag() -> None:
    assert "workflow_dispatch" in WORKFLOW


def test_pyinstaller_can_find_the_package() -> None:
    # Without --paths the analysis misses idle_runner (editable install) and the exe dies on import.
    assert "--paths ." in WORKFLOW
