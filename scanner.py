"""DepFence core: dependency risk scoring engine."""
import json
import re
import requests
from datetime import datetime, timezone
from dataclasses import dataclass, field

from typing import List, Optional, Callable

SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")

@dataclass
class RiskReport:
    name: str
    score: int
    last_release_days: int
    maintainer_count: int
    release_count: int
    verdict: str
    last_release_date: str = ""
    factors: list = field(default_factory=list)

    verdict: str


def parse_deps(path: str) -> List[str]:
    """Extract package names from requirements.txt or package.json."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith(".json"):
        d = json.loads(text)
        deps = {**d.get("dependencies", {}), **d.get("devDependencies", {})}
        return [n for n in deps if SAFE_NAME.match(n)]
    pkgs = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in ("#", "-"):
            continue
        m = re.match(r"^([a-zA-Z0-9][a-zA-Z0-9._-]*)", line)
        if m and SAFE_NAME.match(m.group(1)):
            pkgs.append(m.group(1))
    return pkgs


def fetch_pypi(name: str) -> Optional[dict]:
    """Fetch package metadata from PyPI. Returns None on any failure."""
    if not SAFE_NAME.match(name):
        return None
    try:
        r = requests.get(f"https://pypi.org/pypi/{name}/json", timeout=10)
        return r.json() if r.status_code == 200 else None
    except (requests.RequestException, ValueError):
        return None


def score_package(name: str, data: dict) -> RiskReport:
    """Compute abandonment risk score (0-100) from registry metadata."""
    releases = data.get("releases", {})
    info = data.get("info", {})
    now = datetime.now(timezone.utc)

    # --- latest release age ---
    dates: List[str] = []
    for files in releases.values():
        for f in files:
            t = f.get("upload_time_iso_8601") or f.get("upload_time")
            if t:
                dates.append(t)
    if dates:
        latest = max(dates)
        try:
            dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.strptime(latest, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        days = (now - dt).days
    else:
        days = 9999

    rel_count = sum(1 for f in releases.values() if f)

    # --- maintainer count (distinct roles) ---
    roles = 0
    if info.get("author") or info.get("author_email"):
        roles += 1
    if info.get("maintainer") or info.get("maintainer_email"):
        roles += 1
    mcount = max(roles, 1)

    # --- scoring components ---
    staleness = min(40, max(0, (days - 60) * 40 // 700))
    sparsity = max(0, 30 - rel_count * 2)
    bus = max(0, 30 - (mcount - 1) * 15)

    total = min(staleness + sparsity + bus, 100)
    verdict = (
        "LOW" if total < 25 else "MEDIUM" if total < 50
        else "HIGH" if total < 75 else "CRITICAL"
    )
    return RiskReport(name, total, days, mcount, rel_count, verdict)


def scan(path: str, fetcher: Callable = fetch_pypi) -> List[RiskReport]:
    """Scan dependency file and return risk reports sorted by risk descending."""
    results = []
    for n in parse_deps(path):
        data = fetcher(n)
        if data:
            results.append(score_package(n, data))
        else:
            results.append(RiskReport(n, 100, -1, 0, 0, "UNKNOWN"))
    results.sort(key=lambda x: -x.score)
    return results
