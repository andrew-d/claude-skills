# Skill Mirror — Human Test Plan

## Prerequisites
- Python 3.9+ installed with `pyyaml` package (`pip install pyyaml`)
- `python3 -m pytest test_sync.py -v` passes (33 tests, 0 failures)
- Git installed and able to clone public repositories
- Access to the GitHub repository for workflow inspection
- A copy of `upstream.yaml` in the project root configured with at least one upstream (e.g., `trailofbits`)

## Phase 1: Workflow File Inspection

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | Open `.github/workflows/sync.yaml` in a text editor | File exists and is valid YAML |
| 1.2 | Locate the `on:` block; find `schedule:` | A `cron:` entry is present with value `'0 9 * * 1'` (every Monday at 09:00 UTC) |
| 1.3 | Under `on:`, find `workflow_dispatch:` | `workflow_dispatch: {}` or `workflow_dispatch:` is present, enabling manual triggers |
| 1.4 | Under `jobs:`, find the setup step | `actions/setup-python@v5` is used with `python-version: '3.12'` |
| 1.5 | Find the pip install step | `pip install pyyaml` is present |
| 1.6 | Find the sync execution step | `python sync.py` is called |
| 1.7 | Find the PR creation step | `peter-evans/create-pull-request@v7` is used with `branch:`, `title:`, `commit-message:`, and `body:` fields all specified |

## Phase 2: End-to-End Local Sync (Default Config)

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | Review `upstream.yaml` in the project root; note the configured upstreams and any filters | Config is valid YAML with at least one upstream entry containing `name`, `repo`, and `ref` |
| 2.2 | Run `python3 sync.py` from the project root | Script completes without errors; terminal output shows cloning and copying progress |
| 2.3 | List contents of `plugins/` directory | Directories exist with `{upstream}--{plugin}` naming pattern (e.g., `trailofbits--constant-time-analysis`) |
| 2.4 | For any plugin directory, verify `ls plugins/trailofbits--<plugin>/.claude-plugin/plugin.json` | File exists and contains valid JSON with `name`, `version`, and `description` fields |
| 2.5 | For any plugin directory with skills, verify `ls plugins/trailofbits--<plugin>/skills/` | Skill subdirectories are present, each containing a `SKILL.md` file |
| 2.6 | Open `.claude-plugin/marketplace.json` | File is valid JSON; `plugins` array contains entries for every directory in `plugins/`; each entry has `name`, `source`, `version`, and `description` fields |
| 2.7 | Verify each plugin in `marketplace.json` has a `source` starting with `./plugins/` | All source paths follow the `./plugins/{upstream}--{plugin}` pattern |

## Phase 3: End-to-End Filtering Verification

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | Back up `upstream.yaml`: `cp upstream.yaml upstream.yaml.bak` | Backup created |
| 3.2 | Edit `upstream.yaml` to add a plugin allowlist for one upstream. For example, if the upstream has plugins `[a, b, c]`, set `plugins: { include: [a] }` | Config saved with allowlist |
| 3.3 | Run `python3 sync.py` | Script completes without errors |
| 3.4 | List `plugins/` directory | Only the allowed plugin (with namespace prefix) appears; excluded plugins are absent |
| 3.5 | Edit `upstream.yaml` to use a denylist instead: `plugins: { exclude: [a] }` | Config saved with denylist |
| 3.6 | Run `python3 sync.py` | Script completes without errors |
| 3.7 | List `plugins/` directory | All plugins except the denied one appear |
| 3.8 | Edit `upstream.yaml` to apply skill-level exclusion on one plugin | Config saved |
| 3.9 | Run `python3 sync.py` | Script completes without errors |
| 3.10 | List `plugins/<upstream>--<plugin>/skills/` | The excluded skill directory is absent; other skills are present |
| 3.11 | Restore original config: `cp upstream.yaml.bak upstream.yaml` | Original config restored |

## Phase 4: Workflow Execution (Post-Deployment)

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | Navigate to the GitHub repo, click **Actions** tab | Workflow "Sync upstream skills" is listed |
| 4.2 | Click "Run workflow" button on the workflow page | Manual dispatch triggers the workflow |
| 4.3 | Wait for the run to complete; inspect the log for each step | All steps pass: python setup, pip install, sync.py execution, PR creation |
| 4.4 | Navigate to **Pull Requests** tab | A new PR exists on branch `automated/upstream-sync` with synced plugin changes |
| 4.5 | Run the workflow again immediately without upstream changes | No duplicate PR is created; the action step reports no changes detected |
| 4.6 | After the first Monday at 09:00 UTC following deployment, check **Actions** run history | A scheduled run appears at the expected time |

## Phase 5: README Review

| Step | Action | Expected |
|------|--------|----------|
| 5.1 | Open `README.md` in the project root | File exists |
| 5.2 | Verify it explains the purpose of the repository | A section describes what the repo is (a mirror/aggregator for Claude Code skills from upstream repos) |
| 5.3 | Verify it describes how sync works | Explanation covers: clone upstreams, filter, copy with namespace prefix, generate marketplace.json |
| 5.4 | Verify it documents `upstream.yaml` configuration format | Examples show: basic upstream definition, plugin allowlist, plugin denylist, skill-level include/exclude |
| 5.5 | Verify it covers the security model | Explains that PR diff is the review surface; review changes before merging |
| 5.6 | Verify it includes manual sync instructions | Shows how to run `python sync.py` locally |
| 5.7 | Verify it explains how to add as a Claude Code plugin source | Instructions for pointing Claude Code at the repo |

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| skill-mirror.AC1.1-AC1.9 | 9 tests in `test_sync.py` | -- |
| skill-mirror.AC2.1-AC2.7 | 7 tests in `test_sync.py` | Phase 2, Phase 3 |
| skill-mirror.AC3.1-AC3.4 | 4 tests in `test_sync.py` | Phase 2 steps 2.6-2.7 |
| skill-mirror.AC4.1 | -- | Phase 1 step 1.2 + Phase 4 step 4.6 |
| skill-mirror.AC4.2 | -- | Phase 1 step 1.3 + Phase 4 steps 4.1-4.2 |
| skill-mirror.AC4.3 | -- | Phase 1 steps 1.4-1.6 + Phase 4 step 4.3 |
| skill-mirror.AC4.4 | -- | Phase 1 step 1.7 + Phase 4 steps 4.3-4.4 |
| skill-mirror.AC4.5 | -- | Phase 4 step 4.5 |
| skill-mirror.AC5.1 | -- | Phase 5 steps 5.1-5.7 |
