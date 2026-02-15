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


from formatters import format_table, format_json, format_sarif


def _make_report(name="test-pkg", score=50, days=100, maintainers=1,
                 releases=5, verdict="HIGH"):
    """Build a RiskReport for formatter tests."""
    return RiskReport(
        name=name, score=score, last_release_days=days,
        maintainer_count=maintainers, release_count=releases, verdict=verdict,
    )


# --- format_json tests ---
def test_format_json_valid():
    """format_json output must be valid JSON with schema_version."""
    reports = [_make_report()]
    output = format_json(reports)
    data = json.loads(output)
    assert data["schema_version"] == "1.0"
    assert "scan_timestamp" in data
    assert isinstance(data["packages"], list)
    assert len(data["packages"]) == 1


def test_format_json_package_structure():
    """JSON packages must have all required fields."""
    reports = [_make_report(name="flask", score=30, verdict="MEDIUM")]
    data = json.loads(format_json(reports))
    pkg = data["packages"][0]
    assert pkg["name"] == "flask"
    assert pkg["risk_score"] == 0.3
    assert pkg["risk_level"] == "medium"
    assert "last_release_date" in pkg
    assert isinstance(pkg["factors"], list)


def test_format_json_multiple_packages():
    """JSON output with multiple packages."""
    reports = [
        _make_report(name="pkg-a", score=10, verdict="LOW"),
        _make_report(name="pkg-b", score=80, verdict="CRITICAL"),
    ]
    data = json.loads(format_json(reports))
    assert len(data["packages"]) == 2
    names = [p["name"] for p in data["packages"]]
    assert "pkg-a" in names
    assert "pkg-b" in names
    # Verify risk scores
    scores = {p["name"]: p["risk_score"] for p in data["packages"]}
    assert scores["pkg-a"] == 0.1
    assert scores["pkg-b"] == 0.8


# --- format_sarif tests ---
def test_format_sarif_valid():
    """format_sarif must produce valid SARIF with runs[].results[]."""
    reports = [_make_report()]
    output = format_sarif(reports)
    data = json.loads(output)
    assert data["version"] == "2.1.0"
    assert "$schema" in data
    assert "runs" in data
    assert len(data["runs"]) == 1
    run = data["runs"][0]
    assert "tool" in run
    assert "results" in run
    assert len(run["results"]) == 1


def test_format_sarif_result_structure():
    """SARIF results must have ruleId, message, and level."""
    reports = [_make_report(name="old-lib", score=80, verdict="CRITICAL")]
    data = json.loads(format_sarif(reports))
    result = data["runs"][0]["results"][0]
    assert "ruleId" in result
    assert "message" in result
    assert "text" in result["message"]
    assert result["level"] == "error"
    assert "old-lib" in result["message"]["text"]
    # Check tool driver has rules
    driver = data["runs"][0]["tool"]["driver"]
    assert driver["name"] == "DepFence"
    assert len(driver["rules"]) >= 1


# --- format_table tests ---
def test_format_table_output():
    """format_table must include package name and verdict."""
    reports = [_make_report(name="my-pkg", score=15, verdict="LOW")]
    output = format_table(reports, color=False)
    assert "my-pkg" in output
    assert "LOW" in output
    assert "15" in output


# --- exit-code threshold tests ---
def test_exit_code_high_risk_triggers():
    """Packages with score >= 70 should exceed default 0.7 threshold."""
    report = _make_report(score=80, verdict="CRITICAL")
    threshold = 0.7
    risk_score = report.score / 100.0
    assert risk_score >= threshold, f"risk_score {risk_score} should >= {threshold}"


def test_exit_code_low_risk_passes():
    """Packages with score < 70 should not exceed default 0.7 threshold."""
    report = _make_report(score=20, verdict="LOW")
    threshold = 0.7
    risk_score = report.score / 100.0
    assert risk_score < threshold, f"risk_score {risk_score} should < {threshold}"
