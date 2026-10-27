import io
import json
import urllib.error

from idle_runner.ui import updates
from idle_runner.ui.updates import latest_tag, newer


def test_newer_compares_versions() -> None:
    assert newer("2.0.0", "v2.1.0")
    assert not newer("2.1.0", "v2.1.0")
    assert not newer("2.1.1", "v2.1.0")
    assert newer("2.9.0", "v2.10.0")


def test_a_dev_build_is_older_than_its_release() -> None:
    assert newer("2.0.0.dev0", "v2.0.0")
    assert not newer("2.0.0", "v2.0.0.dev0")


def test_unparsable_tags_are_not_newer() -> None:
    assert not newer("2.0.0", "garbage")
    assert not newer("garbage", "v2.0.0")


def test_latest_tag_reads_the_release(monkeypatch) -> None:
    seen = []

    def fake_urlopen(request, timeout):
        seen.append((request.full_url, timeout))
        return io.BytesIO(json.dumps({"tag_name": "v2.1.0"}).encode())

    monkeypatch.setattr(updates.urllib.request, "urlopen", fake_urlopen)

    assert latest_tag("me/repo", timeout=3) == "v2.1.0"
    assert seen == [("https://api.github.com/repos/me/repo/releases/latest", 3)]


def test_latest_tag_is_none_when_offline(monkeypatch) -> None:
    def offline(request, timeout):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(updates.urllib.request, "urlopen", offline)

    assert latest_tag() is None
