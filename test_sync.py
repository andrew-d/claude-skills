"""Unit tests for sync.py - YAML parsing and filter logic."""

import pytest
import yaml
from sync import (
    load_config,
    parse_plugin_filter,
    parse_skill_filter,
    should_include_plugin,
    should_include_skill,
)


class TestLoadConfig:
    """Test YAML configuration loading."""

    def test_load_config_parses_yaml(self, tmp_path):
        """AC1.1: Parse a config with 2 upstreams, verify both are returned."""
        config_file = tmp_path / "upstream.yaml"
        config_content = """
upstreams:
  - name: trailofbits
    repo: https://github.com/trailofbits/skills
    ref: main
  - name: other
    repo: https://github.com/other/skills
    ref: develop
"""
        config_file.write_text(config_content)

        config = load_config(str(config_file))

        assert len(config["upstreams"]) == 2
        assert config["upstreams"][0]["name"] == "trailofbits"
        assert config["upstreams"][0]["repo"] == "https://github.com/trailofbits/skills"
        assert config["upstreams"][0]["ref"] == "main"
        assert config["upstreams"][1]["name"] == "other"
        assert config["upstreams"][1]["repo"] == "https://github.com/other/skills"
        assert config["upstreams"][1]["ref"] == "develop"


class TestParsePluginFilter:
    """Test plugin-level filter parsing."""

    def test_no_plugins_key_means_all(self):
        """AC1.6: Omitting plugins filter mirrors all plugins."""
        upstream = {"name": "test", "repo": "url", "ref": "main"}

        filter_type, filter_set = parse_plugin_filter(upstream)

        assert filter_type == "all"
        assert filter_set is None

    def test_include_list_creates_include_filter(self):
        """AC1.2: Plugin allowlist include only listed plugins."""
        upstream = {
            "name": "test",
            "repo": "url",
            "ref": "main",
            "plugins": {"include": ["plugin-a", "plugin-b"]},
        }

        filter_type, filter_set = parse_plugin_filter(upstream)

        assert filter_type == "include"
        assert filter_set == {"plugin-a", "plugin-b"}

    def test_exclude_list_creates_exclude_filter(self):
        """AC1.3: Plugin denylist exclude only listed plugins."""
        upstream = {
            "name": "test",
            "repo": "url",
            "ref": "main",
            "plugins": {"exclude": ["plugin-c"]},
        }

        filter_type, filter_set = parse_plugin_filter(upstream)

        assert filter_type == "exclude"
        assert filter_set == {"plugin-c"}

    def test_both_include_and_exclude_raises_error(self):
        """AC1.8: Config with both include and exclude at plugin level raises error."""
        upstream = {
            "name": "test",
            "repo": "url",
            "ref": "main",
            "plugins": {"include": ["a"], "exclude": ["b"]},
        }

        with pytest.raises(ValueError, match="both include and exclude"):
            parse_plugin_filter(upstream)


class TestParseSkillFilter:
    """Test skill-level filter parsing."""

    def test_plain_string_means_all_skills(self):
        """AC1.7: Plugin in include list as plain string means all skills included."""
        plugin_entry = "constant-time-analysis"

        plugin_name, filter_type, filter_set = parse_skill_filter(plugin_entry)

        assert plugin_name == "constant-time-analysis"
        assert filter_type == "all"
        assert filter_set is None

    def test_dict_with_skill_include_filter(self):
        """AC1.4: Skill allowlist include only listed skills within a plugin."""
        plugin_entry = {"building-secure-contracts": {"skills": {"include": ["skill-x"]}}}

        plugin_name, filter_type, filter_set = parse_skill_filter(plugin_entry)

        assert plugin_name == "building-secure-contracts"
        assert filter_type == "include"
        assert filter_set == {"skill-x"}

    def test_dict_with_skill_exclude_filter(self):
        """AC1.5: Skill denylist exclude only listed skills within a plugin."""
        plugin_entry = {"building-secure-contracts": {"skills": {"exclude": ["skill-y"]}}}

        plugin_name, filter_type, filter_set = parse_skill_filter(plugin_entry)

        assert plugin_name == "building-secure-contracts"
        assert filter_type == "exclude"
        assert filter_set == {"skill-y"}

    def test_both_skill_include_and_exclude_raises_error(self):
        """AC1.9: Config with both include and exclude under skills raises ValueError."""
        plugin_entry = {
            "building-secure-contracts": {
                "skills": {"include": ["x"], "exclude": ["y"]}
            }
        }

        with pytest.raises(ValueError, match="both include and exclude"):
            parse_skill_filter(plugin_entry)


class TestShouldIncludePlugin:
    """Test plugin inclusion logic."""

    def test_all_filter_includes_everything(self):
        """All filter type includes any plugin."""
        assert should_include_plugin("plugin-a", "all", None)
        assert should_include_plugin("plugin-z", "all", None)

    def test_include_filter_only_includes_listed(self):
        """Include filter only includes plugins in the set."""
        assert should_include_plugin("plugin-a", "include", {"plugin-a", "plugin-b"})
        assert not should_include_plugin("plugin-c", "include", {"plugin-a", "plugin-b"})

    def test_exclude_filter_excludes_listed(self):
        """Exclude filter includes everything except listed."""
        assert should_include_plugin("plugin-a", "exclude", {"plugin-c"})
        assert not should_include_plugin("plugin-c", "exclude", {"plugin-c"})


class TestShouldIncludeSkill:
    """Test skill inclusion logic."""

    def test_all_filter_includes_everything(self):
        """All filter type includes any skill."""
        assert should_include_skill("skill-a", "all", None)
        assert should_include_skill("skill-z", "all", None)

    def test_include_filter_only_includes_listed(self):
        """Include filter only includes skills in the set."""
        assert should_include_skill("skill-a", "include", {"skill-a", "skill-b"})
        assert not should_include_skill("skill-c", "include", {"skill-a", "skill-b"})

    def test_exclude_filter_excludes_listed(self):
        """Exclude filter includes everything except listed."""
        assert should_include_skill("skill-a", "exclude", {"skill-c"})
        assert not should_include_skill("skill-c", "exclude", {"skill-c"})
