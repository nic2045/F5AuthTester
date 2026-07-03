# PyShell Starter

> Modern starter template for projects that ship **Python** and **PowerShell** side by side.
>
> *Formerly `template-1`. Import path is now `pyshell_starter`; PowerShell module is `PyShellStarter`.*

[![CI - Python](https://github.com/nic2045/template-1/actions/workflows/ci-python.yml/badge.svg)](https://github.com/nic2045/template-1/actions/workflows/ci-python.yml)
[![CI - PowerShell](https://github.com/nic2045/template-1/actions/workflows/ci-powershell.yml/badge.svg)](https://github.com/nic2045/template-1/actions/workflows/ci-powershell.yml)
[![release-please](https://github.com/nic2045/template-1/actions/workflows/release-please.yml/badge.svg)](https://github.com/nic2045/template-1/actions/workflows/release-please.yml)
[![Latest release](https://img.shields.io/github/v/release/nic2045/template-1?sort=semver)](https://github.com/nic2045/template-1/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](pyproject.toml)
[![PowerShell](https://img.shields.io/badge/powershell-5.1%2B%20%7C%20pwsh-blue.svg)](powershell/PyShellStarter.psd1)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://www.conventionalcommits.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Renovate enabled](https://img.shields.io/badge/renovate-enabled-brightgreen.svg)](https://docs.renovatebot.com/)
[![Secret scan: gitleaks](https://github.com/nic2045/pyshell-starter/actions/workflows/gitleaks.yml/badge.svg)](https://github.com/nic2045/pyshell-starter/actions/workflows/gitleaks.yml)

Opinionated starter for hybrid Python + PowerShell projects — batteries included for linting, testing, releases, and dependency hygiene.

Use the green **Use this template** button on GitHub to bootstrap a new project.

## What you get

| Area | Tooling |
| --- | --- |
| Python lint + format | [`ruff`](https://docs.astral.sh/ruff/) |
| Python tests | [`pytest`](https://docs.pytest.org/) |
| PowerShell lint | [`PSScriptAnalyzer`](https://learn.microsoft.com/powershell/utility-modules/psscriptanalyzer/overview) |
| PowerShell tests | [`Pester`](https://pester.dev/) |
| CI | GitHub Actions, path-filtered per language (Python 3.10–3.12, PowerShell on Ubuntu + Windows) |
| Releases | [`release-please`](https://github.com/googleapis/release-please) |
| PR hygiene | Conventional Commits enforced via PR title check |
| Dependencies | Renovate (GitHub Actions + pip, weekly, grouped), auto-merge after CI |
| Secret scanning | [`gitleaks`](https://github.com/gitleaks/gitleaks) on every push, PR, and weekly schedule |
| Editor consistency | `.editorconfig` |

## Repository layout

```
.
├── src/pyshell_starter/     # Python package
├── tests/                   # pytest + Pester tests
├── powershell/              # PowerShell module (psm1 + psd1)
├── .github/
│   ├── workflows/           # ci-python.yml, ci-powershell.yml, release-please.yml, pr-title.yml, release-please-automerge.yml, gitleaks.yml
│   ├── ISSUE_TEMPLATE/
│   └── renovate.json
├── pyproject.toml
├── release-please-config.json
└── .release-please-manifest.json
```

## Getting started

### Python

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

### PowerShell

```powershell
Install-Module -Name PSScriptAnalyzer, Pester -Scope CurrentUser -Force
Invoke-ScriptAnalyzer -Path . -Recurse
Invoke-Pester
```

## Commit & release workflow

All commits and PR titles must follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Meaning | Version bump |
| --- | --- | --- |
| `feat:` | new feature | minor |
| `fix:` | bug fix | patch |
| `feat!:` / `BREAKING CHANGE:` | breaking change | major |
| `chore:`, `docs:`, `refactor:`, `test:`, `ci:`, `build:`, `perf:` | maintenance | none |

When commits land on `main`, [`release-please`](https://github.com/googleapis/release-please) opens (or updates) a release PR. Merging that PR tags a new version and publishes a GitHub release. Versions are kept in sync across `pyproject.toml`, `powershell/PyShellStarter.psd1`, and `src/pyshell_starter/__init__.py`.

## Dependency updates

Dependency PRs are managed by [Renovate](https://docs.renovatebot.com/) via [`.github/renovate.json`](.github/renovate.json):

- **GitHub Actions** updates are grouped, opened weekly with a `ci(deps):` prefix, and auto-merged after CI.
- **pip** minor and patch updates are grouped as `python-minor-patch` with a `build(deps):` prefix and auto-merged after CI.
- **pip** major updates are opened as standalone PRs for manual review.

To activate Renovate on a fork or a repo created from this template, install the [Renovate GitHub App](https://github.com/apps/renovate) and grant it access to the repository. Renovate will pick up `.github/renovate.json` automatically and open an onboarding/dashboard issue on first run.

## After cloning from this template

1. Rename the Python package (`src/pyshell_starter/` and references in `pyproject.toml`, tests).
2. Update `powershell/PyShellStarter.psd1` (GUID, author, description) and rename the module files.
3. Update `README.md` and `LICENSE` (copyright holder).
4. Install the [Renovate GitHub App](https://github.com/apps/renovate) on the new repository so dependency PRs start flowing.
5. In **Settings → General**, enable *Template repository* if you want this repo to be reusable as well.
