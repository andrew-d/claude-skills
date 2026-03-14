# claude-skills

> Upstream skill mirror: syncs Claude Code skill plugins from upstream repos, applies include/exclude filters, and generates a marketplace.json catalog.

Freshness: 2026-03-13

## Purpose

This project mirrors Claude Code skill plugins from upstream Git repositories into a local `plugins/` directory with namespaced names (`{upstream}--{plugin}`). It supports plugin-level and skill-level include/exclude filtering configured via `upstream.yaml`, and generates a `marketplace.json` catalog for consumption.

## Key Files

- `sync.py` -- Main sync script. Entry point: `main()` at bottom. Core pipeline: load_config -> sync_all -> generate_marketplace.
- `test_sync.py` -- 33 pytest tests covering config parsing, filtering, cloning, copying, and marketplace generation.
- `upstream.yaml` -- Declares upstream repos to sync (name, repo URL, ref, optional plugin/skill filters).
- `.github/workflows/sync.yaml` -- Weekly GitHub Actions workflow (Monday 9am UTC) that runs sync and opens a PR.

## Contracts

- **Namespace convention**: Synced plugins are placed at `plugins/{upstream_name}--{plugin_name}/`.
- **Filter mutual exclusivity**: Plugin-level and skill-level configs cannot have both `include` and `exclude` -- raises `ValueError`.
- **Filter types**: Three filter modes: `"all"` (no filter), `"include"` (allowlist), `"exclude"` (denylist). Returned as `(filter_type, filter_set)` tuples.
- **sync_all wipes plugins/**: Each run deletes and recreates the `plugins/` directory. Not incremental.
- **marketplace.json schema**: Top-level keys: `name` ("claude-skills-mirror"), `owner`, `metadata`, `plugins` (sorted by name). Each plugin entry has: `name`, `version`, `description`, `author`, `source`.
- **Shallow clone**: Upstream repos are cloned with `--depth 1`.
- **Temp directory cleanup**: `sync_upstream` uses a `finally` block to clean up temp clone directories.

## upstream.yaml Schema

```yaml
upstreams:
  - name: <string>          # Used as namespace prefix
    repo: <git-url>
    ref: <branch-or-tag>
    plugins:                 # Optional
      include:               # OR exclude (not both)
        - plugin-name        # Plain string = all skills
        - plugin-name:       # Dict = skill-level filtering
            skills:
              include: [...]  # OR exclude (not both)
```

## Invariants

- The `plugins/` directory and `.claude-plugin/marketplace.json` are generated artifacts -- do not commit manually.
- `.tmp-upstream-*` directories are transient (in `.gitignore`).
- Clone failures are logged and skipped (do not abort the entire sync).
- Upstream repos missing a `plugins/` directory are warned and skipped.

## Python Package Management with uv

Use uv exclusively for Python package management in this project.

## Package Management Commands

- All Python dependencies **must be installed, synchronized, and locked** using uv
- Never use pip, pip-tools, poetry, or conda directly for dependency management

Use these commands:

- Install dependencies: `uv add <package>`
- Remove dependencies: `uv remove <package>`
- Sync dependencies: `uv sync`

## Running Python Code

- Run a Python script with `uv run <script-name>.py`
- Run Python tools like Pytest with `uv run pytest` or `uv run ruff`
- Launch a Python repl with `uv run python`

## Managing Scripts with PEP 723 Inline Metadata

- Run a Python script with inline metadata (dependencies defined at the top of the file) with: `uv run script.py`
- You can add or remove dependencies manually from the `dependencies =` section at the top of the script, or
- Or using uv CLI:
    - `uv add package-name --script script.py`
    - `uv remove package-name --script script.py`
