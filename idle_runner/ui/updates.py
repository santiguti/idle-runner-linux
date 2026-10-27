"""Update check: is there a newer release on GitHub? Never raises; offline just means no answer."""
import json
import re
import urllib.request

from idle_runner import REPO

_VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(?:\.dev(\d+))?")


def _key(version: str) -> tuple[int, int, int, int] | None:
    found = _VERSION.fullmatch(version.strip())
    if not found:
        return None
    major, minor, patch, dev = found.groups()
    return int(major), int(minor), int(patch), 0 if dev is not None else 1  # 2.0.0.dev0 < 2.0.0


def newer(current: str, latest_tag: str) -> bool:
    current_key, latest_key = _key(current), _key(latest_tag)
    return current_key is not None and latest_key is not None and latest_key > current_key


def latest_tag(repo: str = REPO, timeout: float = 5) -> str | None:
    """Tag of the repository's latest release, or None on any error."""
    request = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest",
                                     headers={"Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)["tag_name"]
    except Exception:  # offline, rate limit, no release yet, bad JSON: all mean "don't know"
        return None
