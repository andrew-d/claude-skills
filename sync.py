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


def should_include_plugin(
    plugin_name: str, filter_type: str, filter_set: Optional[Set[str]]
) -> bool:
    """Determine if a plugin should be included based on filter.

    Args:
        plugin_name: Name of the plugin
        filter_type: "all", "include", or "exclude"
        filter_set: Set of plugin names (None if filter_type is "all")

    Returns:
        True if plugin should be included, False otherwise
    """
    if filter_type == "all":
        return True
    elif filter_type == "include":
        return plugin_name in filter_set
    elif filter_type == "exclude":
        return plugin_name not in filter_set
    else:
        raise ValueError(f"Unknown filter_type: {filter_type}")


def should_include_skill(
    skill_name: str, filter_type: str, filter_set: Optional[Set[str]]
) -> bool:
    """Determine if a skill should be included based on filter.

    Args:
        skill_name: Name of the skill
        filter_type: "all", "include", or "exclude"
        filter_set: Set of skill names (None if filter_type is "all")

    Returns:
        True if skill should be included, False otherwise
    """
    if filter_type == "all":
        return True
    elif filter_type == "include":
        return skill_name in filter_set
    elif filter_type == "exclude":
        return skill_name not in filter_set
    else:
        raise ValueError(f"Unknown filter_type: {filter_type}")


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
    shutil.copytree(src_plugin_dir, dest_plugin_dir)

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
            logger.error(f"Failed to clone upstream {upstream['name']}: {e}")
            return []

        # Check for plugins directory
        src_plugins_dir = Path(temp_dir) / "plugins"
        if not src_plugins_dir.exists():
            logger.warning(
                f"Upstream {upstream['name']} has no plugins/ directory, skipping"
            )
            return []

        # Parse plugin filter
        plugin_filter_type, plugin_filter_set = parse_plugin_filter(upstream)

        created_plugins = []
        plugins_dir_path = Path(plugins_dir)

        # Process each plugin in the upstream
        for plugin_dir in src_plugins_dir.iterdir():
            if not plugin_dir.is_dir():
                continue

            plugin_name = plugin_dir.name

            # Check if plugin should be included
            if not should_include_plugin(plugin_name, plugin_filter_type, plugin_filter_set):
                continue

            # Parse skill filter for this plugin if in include list
            skill_filter_type = "all"
            skill_filter_set = None

            if plugin_filter_type == "include":
                # Find the plugin entry in the include list
                include_list = upstream.get("plugins", {}).get("include", [])
                for entry in include_list:
                    if isinstance(entry, str) and entry == plugin_name:
                        skill_filter_type = "all"
                        skill_filter_set = None
                        break
                    elif isinstance(entry, dict):
                        parsed_name, skill_type, skill_set = parse_skill_filter(entry)
                        if parsed_name == plugin_name:
                            skill_filter_type = skill_type
                            skill_filter_set = skill_set
                            break

            # Create namespaced plugin name
            namespaced_name = f"{upstream['name']}--{plugin_name}"
            dest_plugin_dir = str(plugins_dir_path / namespaced_name)

            # Copy plugin with filtering
            copy_plugin(
                str(plugin_dir), dest_plugin_dir, skill_filter_type, skill_filter_set
            )

            created_plugins.append(namespaced_name)

        return created_plugins

    finally:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir)


def sync_all(config_path: str = "upstream.yaml") -> list:
    """Sync all upstream repositories.

    Args:
        config_path: Path to upstream.yaml

    Returns:
        List of all created plugin names
    """
    config = load_config(config_path)

    # Clear and recreate plugins directory
    plugins_dir = Path("plugins")
    if plugins_dir.exists():
        shutil.rmtree(plugins_dir)
    plugins_dir.mkdir()

    all_created_plugins = []

    for upstream in config.get("upstreams", []):
        created = sync_upstream(upstream, str(plugins_dir))
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


def main() -> None:
    """Main entry point."""
    created_plugins = sync_all()
    logger.info(f"Created {len(created_plugins)} plugins")

    # Generate marketplace
    generate_marketplace("plugins", ".claude-plugin/marketplace.json")
    logger.info("Generated marketplace.json")


if __name__ == "__main__":
    main()
