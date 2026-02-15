"""DepFence test suite — 7 tests covering parsing, scoring, and integration."""
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta

from scanner import parse_deps, score_package, scan, RiskReport


def _pypi(days_ago=30, releases=10, author="alice", maintainer="bob"):
    """Build a fake PyPI metadata dict for testing."""
    ts = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    rels = {f"{i}.0": [{"upload_time_iso_8601": ts}] for i in range(releases)}
    return {
        "info": {
            "author": author or None,
            "maintainer": maintainer or None,
            "author_email": f"{author}@e" if author else None,
            "maintainer_email": f"{maintainer}@e" if maintainer else None,
        },
        "releases": rels,
    }


def _tmp(content, suffix=".txt"):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    f.write(content)
    f.flush()
    f.close()
    return f.name


# --- parsing ---
def test_parse_requirements():
    p = _tmp("requests>=2.28\nflask==2.0\n# comment\n-e git+foo\nnumpy\n")
    assert parse_deps(p) == ["requests", "flask", "numpy"]
    os.unlink(p)


def test_parse_package_json():
    data = json.dumps({"dependencies": {"express": "^4"}, "devDependencies": {"jest": "*"}})
    p = _tmp(data, ".json")
    assert set(parse_deps(p)) == {"express", "jest"}
    os.unlink(p)


# --- scoring ---
def test_healthy_package_low_risk():
    r = score_package("good-lib", _pypi(days_ago=10, releases=20, author="a", maintainer="b"))
    assert r.score < 25, f"expected LOW, got {r.score}"
    assert r.verdict == "LOW"


def test_abandoned_package_critical():
    r = score_package("dead-lib", _pypi(days_ago=800, releases=2, author="x", maintainer=""))
    assert r.score >= 50, f"expected HIGH+, got {r.score}"
    assert r.verdict in ("HIGH", "CRITICAL")


def test_bus_factor_one_adds_risk():
    r = score_package("solo", _pypi(days_ago=30, releases=15, author="me", maintainer=""))
    assert r.maintainer_count == 1
    assert r.score >= 30, f"bus-factor-1 should add risk, got {r.score}"


# --- integration ---
def test_scan_sorts_by_risk_descending():
    p = _tmp("old-pkg\nnew-pkg\n")
    fetcher = lambda n: _pypi(days_ago=600) if n == "old-pkg" else _pypi(days_ago=5)
    res = scan(p, fetcher=fetcher)
    os.unlink(p)
    assert len(res) == 2
    assert res[0].name == "old-pkg"
    assert res[0].score > res[1].score


def test_unknown_package_scores_max():
    p = _tmp("nonexistent\n")
    res = scan(p, fetcher=lambda n: None)
    os.unlink(p)
    assert res[0].verdict == "UNKNOWN"
    assert res[0].score == 100


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"  \u2713 {name}")
    print("All tests passed!")
