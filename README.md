# Claude Skills Mirror

A curated mirror of Claude Code skills from trusted upstream repositories, with automated syncing and review workflows.

## What This Repo Is

This repository maintains a mirror of skills from upstream repositories. Skills are curated to include only those from trusted sources, and the mirror is kept in sync via automated syncing and pull request workflows. Users can configure Claude Code to use this repository as a plugin source.

## How It Works

The syncing process consists of three main steps:

1. **Clone upstreams** — `sync.py` clones all configured upstream repositories
2. **Apply filters** — Skills are filtered based on configuration (plugin-level and skill-level allowlist/denylist)
3. **Generate marketplace** — A `marketplace.json` file is generated for Claude Code to discover available skills

The GitHub Action (`sync.yaml`) runs this process on a weekly schedule and on manual trigger. When changes are detected, it creates a pull request with the updates. The PR diff becomes the review surface—review all changes before merging.

## Configuration Format

Configuration is defined in `upstream.yaml`. The schema is:

```yaml
upstreams:
  - name: <upstream-name>           # Unique identifier for this upstream
    repo: <git-url>                 # Git repository URL
    ref: <branch/tag>               # Git reference (branch or tag)
    plugins:                        # (Optional) Plugin-level filtering
      include:                      # (Optional) Only include these plugins
        - <plugin-name>
        - plugin-name:
            skills:                 # (Optional) Skill-level filtering
              include:              # (Optional) Only include these skills
                - <skill-name>
              exclude:              # (Optional) Exclude these skills
                - <skill-name>
      exclude:                      # (Optional) Exclude these plugins
        - <plugin-name>
```

### Configuration Examples

#### Mirror all plugins (no filters)

```yaml
upstreams:
  - name: trailofbits
    repo: https://github.com/trailofbits/skills
    ref: main
```

All plugins and skills from the repository are included.

#### Plugin-level allowlist

```yaml
upstreams:
  - name: security-tools
    repo: https://github.com/example/skills
    ref: main
    plugins:
      include:
        - security-analysis
        - vulnerability-scanner
```

Only plugins named `security-analysis` and `vulnerability-scanner` are included.

#### Plugin-level denylist

```yaml
upstreams:
  - name: experimental
    repo: https://github.com/example/skills
    ref: main
    plugins:
      exclude:
        - unstable-plugin
        - beta-feature
```

All plugins except `unstable-plugin` and `beta-feature` are included.

#### Skill-level filtering within a plugin

```yaml
upstreams:
  - name: mixed-tools
    repo: https://github.com/example/skills
    ref: main
    plugins:
      include:
        - analysis-plugin:
            skills:
              include:
                - code-review
                - type-checking
        - utils-plugin:
            skills:
              exclude:
                - deprecated-util
```

- Plugin `analysis-plugin` is included, but only with skills `code-review` and `type-checking`
- Plugin `utils-plugin` is included with all skills except `deprecated-util`
- Other plugins are excluded

## Security Model

Security depends on careful review:

- **PR as review surface** — Every sync creates a PR with a diff of changes. Review the diff carefully before merging.
- **Skills contain instructions** — Skills can include instructions that affect Claude's behavior. Understand what you're adding.
- **Trust upstream sources** — Only add upstreams you trust. Assume that any skill you merge will influence Claude's behavior.

When reviewing a sync PR, check:

1. Are the changed skills from expected upstreams?
2. Do the changes match what you intended to sync?
3. Are there any suspicious or unexpected additions?

## Manual Sync

To run the sync process locally:

```bash
python sync.py
```

This will:

1. Clone or update all configured upstream repositories
2. Filter skills according to `upstream.yaml`
3. Copy filtered skills to `plugins/`
4. Generate `marketplace.json` with skill metadata

No dependencies are needed beyond Python 3.12 and PyYAML:

```bash
pip install pyyaml
```

## Using This As a Claude Code Plugin Source

To configure Claude Code to use this repository as a plugin source:

1. Install this repository as a plugin source in your Claude Code configuration
2. Claude Code will read the `marketplace.json` file to discover available skills
3. Skills will be available for use in Claude Code sessions

Refer to Claude Code documentation for exact configuration steps for your environment.
