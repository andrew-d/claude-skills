"""Sync upstream skills repositories and generate marketplace.json."""

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Set, Tuple

import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    """Load and parse upstream.yaml configuration.

    Args:
        path: Path to upstream.yaml file

    Returns:
        Parsed configuration dictionary
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)


def parse_plugin_filter(upstream: dict) -> Tuple[str, Optional[Set[str]]]:
    """Parse plugin-level filter from upstream config.

    Args:
        upstream: Upstream configuration dictionary

    Returns:
        Tuple of (filter_type, filter_set) where filter_type is one of:
        - "all": no filtering (both include and exclude are None)
        - "include": only listed plugins included
        - "exclude": listed plugins excluded
        filter_set is None for "all", otherwise a set of plugin names

    Raises:
        ValueError: If both include and exclude are specified
    """
    if "plugins" not in upstream:
        return "all", None

    plugins_config = upstream["plugins"]

    if "include" in plugins_config and "exclude" in plugins_config:
        raise ValueError(
            "upstream config cannot have both include and exclude at plugin level"
        )

    if "include" in plugins_config:
        # Include list can have both strings and dicts
        plugin_names = set()
        for entry in plugins_config["include"]:
            if isinstance(entry, str):
                plugin_names.add(entry)
            elif isinstance(entry, dict):
                # Dict key is the plugin name
                plugin_names.add(list(entry.keys())[0])
        return "include", plugin_names

    if "exclude" in plugins_config:
        return "exclude", set(plugins_config["exclude"])

    return "all", None


def parse_skill_filter(plugin_entry) -> Tuple[str, str, Optional[Set[str]]]:
    """Parse skill-level filter from a plugin entry.

    A plugin entry can be either:
    - A plain string: "plugin-name" (all skills included)
    - A dict: {"plugin-name": {"skills": {include/exclude: [...]}}}

    Args:
        plugin_entry: Plugin entry from config

    Returns:
        Tuple of (plugin_name, filter_type, filter_set) where:
        - plugin_name: Name of the plugin
        - filter_type: "all", "include", or "exclude"
        - filter_set: None for "all", otherwise a set of skill names

    Raises:
        ValueError: If both include and exclude are specified
    """
    # Plain string case
    if isinstance(plugin_entry, str):
        return plugin_entry, "all", None

    # Dict case
    if isinstance(plugin_entry, dict):
        plugin_name = list(plugin_entry.keys())[0]
        plugin_config = plugin_entry[plugin_name]

        if "skills" not in plugin_config:
            return plugin_name, "all", None

        skills_config = plugin_config["skills"]

        if "include" in skills_config and "exclude" in skills_config:
            raise ValueError(
                "upstream config cannot have both include and exclude at skill level"
            )

        if "include" in skills_config:
            return plugin_name, "include", set(skills_config["include"])

        if "exclude" in skills_config:
            return plugin_name, "exclude", set(skills_config["exclude"])

        return plugin_name, "all", None

    raise ValueError(f"Unexpected plugin entry format: {plugin_entry}")


def should_include(
    name: str, filter_type: str, filter_set: Optional[Set[str]]
) -> bool:
    """Determine if an item should be included based on filter.

    Args:
        name: Name of the item (plugin or skill)
        filter_type: "all", "include", or "exclude"
        filter_set: Set of item names (None if filter_type is "all")

    Returns:
        True if item should be included, False otherwise
    """
    if filter_type == "all":
        return True
    elif filter_type == "include":
        return name in filter_set
    elif filter_type == "exclude":
        return name not in filter_set
    else:
        raise ValueError(f"Unknown filter_type: {filter_type}")


# Backwards compatibility aliases
def should_include_plugin(
    plugin_name: str, filter_type: str, filter_set: Optional[Set[str]]
) -> bool:
    """Determine if a plugin should be included based on filter.

    Deprecated: Use should_include() instead.
    """
    return should_include(plugin_name, filter_type, filter_set)


def should_include_skill(
    skill_name: str, filter_type: str, filter_set: Optional[Set[str]]
) -> bool:
    """Determine if a skill should be included based on filter.

    Deprecated: Use should_include() instead.
    """
    return should_include(skill_name, filter_type, filter_set)


def read_upstream_marketplace(clone_dir: str) -> Optional[dict]:
    """Read marketplace.json from a cloned upstream repository.

    Args:
        clone_dir: Path to cloned repository

    Returns:
        Parsed marketplace.json dict, or None if not found
    """
    marketplace_path = Path(clone_dir) / ".claude-plugin" / "marketplace.json"
    if not marketplace_path.exists():
        return None
    with open(marketplace_path, "r") as f:
        return json.load(f)


def extract_marketplace_skills(plugin_entry: dict) -> Optional[Set[str]]:
    """Extract skill directory names from a marketplace plugin entry.

    Marketplace entries may have a 'skills' array with paths like
    './skills/codable-patterns'. This extracts just the directory names.

    Args:
        plugin_entry: A single plugin entry from marketplace.json

    Returns:
        Set of skill directory names, or None if no skills key
    """
    skills = plugin_entry.get("skills")
    if not skills:
        return None
    return {Path(skill_path).name for skill_path in skills}


def compute_effective_skill_filter(
    marketplace_skills: Optional[Set[str]],
    user_filter_type: str,
    user_filter_set: Optional[Set[str]],
) -> Tuple[str, Optional[Set[str]]]:
    """Compose marketplace-declared skills with user-configured skill filter.

    When a marketplace entry declares specific skills, those act as a base
    include set. The user's filter is then applied on top.

    Args:
        marketplace_skills: Skills declared in marketplace entry (None = no restriction)
        user_filter_type: User's skill filter type ("all", "include", "exclude")
        user_filter_set: User's skill filter set

    Returns:
        Tuple of (effective_filter_type, effective_filter_set)
    """
    if marketplace_skills is None:
        return user_filter_type, user_filter_set

    allowed = set(marketplace_skills)

    if user_filter_type == "include":
        allowed = allowed & user_filter_set
    elif user_filter_type == "exclude":
        allowed = allowed - user_filter_set

    return "include", allowed


def _get_user_skill_filter(
    upstream: dict, plugin_name: str, plugin_filter_type: str
) -> Tuple[str, Optional[Set[str]]]:
    """Look up user-configured skill filter for a specific plugin.

    Args:
        upstream: Upstream configuration dictionary
        plugin_name: Name of the plugin to look up
        plugin_filter_type: The plugin-level filter type

    Returns:
        Tuple of (filter_type, filter_set)
    """
    if plugin_filter_type != "include":
        return "all", None
    include_list = upstream.get("plugins", {}).get("include", [])
    for entry in include_list:
        if isinstance(entry, str) and entry == plugin_name:
            return "all", None
        elif isinstance(entry, dict):
            parsed_name, skill_type, skill_set = parse_skill_filter(entry)
            if parsed_name == plugin_name:
                return skill_type, skill_set
    return "all", None


def clone_upstream(repo_url: str, ref: str, dest: str) -> None:
    """Clone an upstream repository to a destination.

    Args:
        repo_url: Git repository URL
        ref: Git ref (branch/tag)
        dest: Destination directory

    Raises:
        subprocess.CalledProcessError: If clone fails
    """
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", ref, repo_url, dest],
        check=True,
        capture_output=True,
    )


def copy_plugin(
    src_plugin_dir: str,
    dest_plugin_dir: str,
    skill_filter_type: str,
    skill_filter_set: Optional[Set[str]],
) -> None:
    """Copy a plugin directory with skill-level filtering.

    Args:
        src_plugin_dir: Source plugin directory
        dest_plugin_dir: Destination plugin directory
        skill_filter_type: "all", "include", or "exclude"
        skill_filter_set: Set of skill names to filter (None if filter_type is "all")
    """
    shutil.copytree(
        src_plugin_dir, dest_plugin_dir, ignore=shutil.ignore_patterns(".git")
    )

    # Apply skill-level filtering if needed
    if skill_filter_type != "all":
        skills_dir = Path(dest_plugin_dir) / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    skill_name = skill_dir.name
                    if not should_include_skill(
                        skill_name, skill_filter_type, skill_filter_set
                    ):
                        shutil.rmtree(skill_dir)


def sync_upstream(upstream: dict, plugins_dir: str) -> list:
    """Sync a single upstream repository.

    Discovers plugins by reading the upstream's .claude-plugin/marketplace.json.
    Falls back to scanning a plugins/ directory if no marketplace.json exists.

    Args:
        upstream: Upstream configuration dictionary
        plugins_dir: Destination plugins directory

    Returns:
        List of created plugin names (with namespace prefix)
    """
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=".tmp-upstream-")

        # Clone the upstream
        try:
            clone_upstream(upstream["repo"], upstream["ref"], temp_dir)
        except subprocess.CalledProcessError as e:
            logger.error("Failed to clone upstream %s: %s", upstream['name'], e)
            return []

        # Try marketplace-based discovery first
        marketplace = read_upstream_marketplace(temp_dir)
        if marketplace:
            return _sync_from_marketplace(upstream, temp_dir, plugins_dir, marketplace)

        # Fall back to scanning plugins/ directory
        return _sync_from_plugins_dir(upstream, temp_dir, plugins_dir)

    finally:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir)


def _sync_from_marketplace(
    upstream: dict, clone_dir: str, plugins_dir: str, marketplace: dict
) -> list:
    """Sync plugins discovered via upstream marketplace.json.

    Args:
        upstream: Upstream configuration dictionary
        clone_dir: Path to cloned repository
        plugins_dir: Destination plugins directory
        marketplace: Parsed marketplace.json

    Returns:
        List of created plugin names (with namespace prefix)
    """
    plugin_filter_type, plugin_filter_set = parse_plugin_filter(upstream)
    created_plugins = []
    plugins_dir_path = Path(plugins_dir)

    for mp_entry in marketplace.get("plugins", []):
        plugin_name = mp_entry["name"]

        if not should_include(plugin_name, plugin_filter_type, plugin_filter_set):
            continue

        # Resolve source path relative to clone dir
        source = mp_entry.get("source", "./")
        if source in ("./", "."):
            source_path = Path(clone_dir)
        else:
            source_path = Path(clone_dir) / source.removeprefix("./")

        if not source_path.exists():
            logger.warning(
                "Plugin %s source path %s not found, skipping",
                plugin_name,
                source,
            )
            continue

        # Get marketplace-declared skills and user skill filter, then compose
        marketplace_skills = extract_marketplace_skills(mp_entry)
        user_skill_type, user_skill_set = _get_user_skill_filter(
            upstream, plugin_name, plugin_filter_type
        )
        eff_type, eff_set = compute_effective_skill_filter(
            marketplace_skills, user_skill_type, user_skill_set
        )

        # Copy plugin with effective skill filter
        namespaced_name = f"{upstream['name']}--{plugin_name}"
        dest_plugin_dir = str(plugins_dir_path / namespaced_name)
        copy_plugin(str(source_path), dest_plugin_dir, eff_type, eff_set)

        # Ensure .claude-plugin/plugin.json exists for marketplace generation.
        # Shared-root repos may only have marketplace.json, not plugin.json.
        dest_plugin_json = Path(dest_plugin_dir) / ".claude-plugin" / "plugin.json"
        if not dest_plugin_json.exists():
            dest_plugin_json.parent.mkdir(parents=True, exist_ok=True)
            plugin_meta = {
                "name": plugin_name,
                "version": mp_entry.get("version", "0.0.0"),
                "description": mp_entry.get("description", ""),
                "author": mp_entry.get("author", {}),
            }
            with open(dest_plugin_json, "w") as f:
                json.dump(plugin_meta, f, indent=2)

        created_plugins.append(namespaced_name)

    return created_plugins


def _sync_from_plugins_dir(
    upstream: dict, clone_dir: str, plugins_dir: str
) -> list:
    """Sync plugins by scanning the plugins/ directory (fallback).

    Used when the upstream repo has no .claude-plugin/marketplace.json.

    Args:
        upstream: Upstream configuration dictionary
        clone_dir: Path to cloned repository
        plugins_dir: Destination plugins directory

    Returns:
        List of created plugin names (with namespace prefix)
    """
    src_plugins_dir = Path(clone_dir) / "plugins"
    if not src_plugins_dir.exists():
        logger.warning(
            "Upstream %s has no marketplace.json or plugins/ directory, skipping",
            upstream['name'],
        )
        return []

    plugin_filter_type, plugin_filter_set = parse_plugin_filter(upstream)
    created_plugins = []
    plugins_dir_path = Path(plugins_dir)

    for plugin_dir in src_plugins_dir.iterdir():
        if not plugin_dir.is_dir():
            continue

        plugin_name = plugin_dir.name

        if not should_include(plugin_name, plugin_filter_type, plugin_filter_set):
            continue

        user_skill_type, user_skill_set = _get_user_skill_filter(
            upstream, plugin_name, plugin_filter_type
        )

        namespaced_name = f"{upstream['name']}--{plugin_name}"
        dest_plugin_dir = str(plugins_dir_path / namespaced_name)
        copy_plugin(str(plugin_dir), dest_plugin_dir, user_skill_type, user_skill_set)
        created_plugins.append(namespaced_name)

    return created_plugins


def sync_all(config_path: str = "upstream.yaml", plugins_dir: str = "plugins") -> list:
    """Sync all upstream repositories.

    Args:
        config_path: Path to upstream.yaml
        plugins_dir: Destination directory for plugins (default: "plugins")

    Returns:
        List of all created plugin names
    """
    config = load_config(config_path)

    # Clear and recreate plugins directory
    plugins_dir_path = Path(plugins_dir)
    if plugins_dir_path.exists():
        shutil.rmtree(plugins_dir_path)
    plugins_dir_path.mkdir()

    all_created_plugins = []

    for upstream in config.get("upstreams", []):
        created = sync_upstream(upstream, str(plugins_dir_path))
        all_created_plugins.extend(created)

    return all_created_plugins


def generate_marketplace(plugins_dir: str, output_path: str) -> None:
    """Generate marketplace.json from plugins directory.

    Args:
        plugins_dir: Directory containing plugins
        output_path: Path where marketplace.json will be written
    """
    plugins_data = []

    plugins_dir_basename = Path(plugins_dir).name

    for plugin_dir in sorted(Path(plugins_dir).iterdir()):
        if not plugin_dir.is_dir():
            continue

        plugin_json_path = plugin_dir / ".claude-plugin" / "plugin.json"
        if not plugin_json_path.exists():
            continue

        with open(plugin_json_path, "r") as f:
            plugin_json = json.load(f)

        plugin_entry = {
            "name": plugin_dir.name,
            "version": plugin_json.get("version"),
            "description": plugin_json.get("description"),
            "author": plugin_json.get("author", {}),
            "source": f"./{plugins_dir_basename}/{plugin_dir.name}",
        }

        plugins_data.append(plugin_entry)

    # Sort by name
    plugins_data.sort(key=lambda p: p["name"])

    marketplace = {
        "name": "claude-skills-mirror",
        "owner": {"name": "Mirrored"},
        "metadata": {
            "version": "1.0.0",
            "description": "Curated Claude Code plugins mirrored from upstream repositories",
        },
        "plugins": plugins_data,
    }

    # Ensure output directory exists
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(marketplace, f, indent=2)


def main(
    config_path: str = "upstream.yaml",
    plugins_dir: str = "plugins",
    marketplace_output_path: str = ".claude-plugin/marketplace.json",
) -> None:
    """Main entry point.

    Args:
        config_path: Path to upstream.yaml (default: "upstream.yaml")
        plugins_dir: Destination directory for plugins (default: "plugins")
        marketplace_output_path: Path for marketplace.json output (default: ".claude-plugin/marketplace.json")
    """
    created_plugins = sync_all(config_path, plugins_dir)
    logger.info("Created %s plugins", len(created_plugins))

    # Generate marketplace
    generate_marketplace(plugins_dir, marketplace_output_path)
    logger.info("Generated marketplace.json")


if __name__ == "__main__":
    main()
