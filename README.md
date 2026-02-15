# 🛡️ DepFence — Dependency Maintainer Risk Intelligence Scanner

> Quantify "will someone still maintain this next year?" risk for every dependency — before the next xz-utils happens to you.

DepFence scans your `requirements.txt` or `package.json`, queries package registries, and computes an **abandonment risk score (0–100)** based on staleness, release cadence, and bus factor.

## 🚀 Quick Start

```bash
pip install -r requirements.txt

# Scan your Python project
python depfence.py requirements.txt

# JSON output for CI pipelines
python depfence.py requirements.txt --json

# Fail CI if any dependency scores >= 50
python depfence.py requirements.txt --fail-over 50
```

## 📊 Risk Scoring Algorithm

| Signal | Weight | What it measures |
|---|---|---|
| Staleness | 0–40 | Days since last release (>60 days starts accruing) |
| Release Sparsity | 0–30 | Total release count (fewer = riskier) |
| Bus Factor | 0–30 | Number of distinct maintainer roles |

**Verdicts:** LOW (<25) · MEDIUM (25–49) · HIGH (50–74) · CRITICAL (75–100)

## 💰 Pricing

| Feature | Free | Pro $49/mo | Enterprise $499/mo |
|---|:---:|:---:|:---:|
| Dependencies scanned | 20 | Unlimited | Unlimited |
| PyPI + npm support | ✅ | ✅ | ✅ |
| CLI + JSON output | ✅ | ✅ | ✅ |
| CI gate (`--fail-over`) | ✅ | ✅ | ✅ |
| GitHub/crates.io/Go modules | — | ✅ | ✅ |
| SARIF + CycloneDX SBOM export | — | ✅ | ✅ |
| Historical trend tracking | — | ✅ | ✅ |
| GitHub Actions integration | — | ✅ | ✅ |
| Alternative package suggestions | — | ✅ | ✅ |
| SaaS dashboard + alerts | — | — | ✅ |
| SOC2/ISO27001 compliance reports | — | — | ✅ |
| SSO + team management | — | — | ✅ |
| SLA + priority support | — | — | ✅ |

## 🤔 Why Pay?

**The xz-utils backdoor cost the industry millions.** A single abandoned or silently-transferred dependency can compromise your entire supply chain.

DepFence Pro gives you:
- **Full visibility** across all ecosystems (not just PyPI/npm)
- **Trend detection** — catch declining activity before abandonment
- **Compliance artifacts** that SOC2 auditors actually accept
- **Actionable alternatives** — not just "this is risky" but "switch to X"

> "We caught 3 abandoned transitive deps in our Go service before SOC2 audit. Saved us weeks." — *SRE Lead, Series B startup*

## 🔒 Security Design

- All package names validated against strict regex before network use
- Network errors treated as UNKNOWN (score=100) — **fail-safe by default**
- No secrets, tokens, or credentials required for free tier
- Zero dependency on third-party scoring services

## License

BSL 1.1 — Free for evaluation and small teams. Commercial license required for organizations >25 employees.
