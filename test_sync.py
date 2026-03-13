"""Unit tests for sync.py - YAML parsing and filter logic."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from sync import (
    clone_upstream,
    copy_plugin,
    load_config,
    parse_plugin_filter,
    parse_skill_filter,
    should_include_plugin,
    should_include_skill,
    sync_upstream,
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


class TestCloneUpstream:
    """Test upstream repository cloning."""

    def test_clone_upstream_calls_git_correctly(self):
        """AC2.1: Verify clone_upstream calls git with correct args."""
        with patch("subprocess.run") as mock_run:
            clone_upstream("https://github.com/test/repo", "main", "/tmp/test")

            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                "main",
                "https://github.com/test/repo",
                "/tmp/test",
            ]
            assert call_args[1]["check"] is True

    def test_clone_upstream_raises_on_failure(self):
        """Clone raises CalledProcessError on git failure."""
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            with pytest.raises(subprocess.CalledProcessError):
                clone_upstream("https://bad-repo", "main", "/tmp/test")


class TestCopyPlugin:
    """Test plugin directory copying."""

    def test_copy_plugin_copies_directory_structure(self, tmp_path):
        """AC2.3: Create fake plugin with nested dirs, verify all copied."""
        # Create source structure
        src_plugin = tmp_path / "src_plugin"
        src_plugin.mkdir()
        (src_plugin / ".claude-plugin").mkdir()
        (src_plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "test"}')
        (src_plugin / "skills").mkdir()
        skill_dir = src_plugin / "skills" / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Test")
        resources_dir = skill_dir / "resources"
        resources_dir.mkdir()
        (resources_dir / "doc.md").write_text("Resource")

        dest_plugin = tmp_path / "dest_plugin"

        copy_plugin(str(src_plugin), str(dest_plugin), "all", None)

        # Verify structure is copied
        assert (dest_plugin / ".claude-plugin" / "plugin.json").exists()
        assert (dest_plugin / "skills" / "test-skill" / "SKILL.md").exists()
        assert (dest_plugin / "skills" / "test-skill" / "resources" / "doc.md").exists()

    def test_copy_plugin_with_exclude_filter(self, tmp_path):
        """AC2.4: Create fake plugin with skills [a,b,c], exclude b, verify result."""
        # Create source structure with multiple skills
        src_plugin = tmp_path / "src_plugin"
        src_plugin.mkdir()
        (src_plugin / "skills").mkdir()

        for skill in ["skill-a", "skill-b", "skill-c"]:
            skill_dir = src_plugin / "skills" / skill
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# {skill}")

        dest_plugin = tmp_path / "dest_plugin"

        copy_plugin(str(src_plugin), str(dest_plugin), "exclude", {"skill-b"})

        # Verify b is removed, a and c exist
        assert (dest_plugin / "skills" / "skill-a" / "SKILL.md").exists()
        assert (dest_plugin / "skills" / "skill-c" / "SKILL.md").exists()
        assert not (dest_plugin / "skills" / "skill-b").exists()

    def test_copy_plugin_with_include_filter(self, tmp_path):
        """Copy with include filter only keeps specified skills."""
        src_plugin = tmp_path / "src_plugin"
        src_plugin.mkdir()
        (src_plugin / "skills").mkdir()

        for skill in ["skill-a", "skill-b", "skill-c"]:
            skill_dir = src_plugin / "skills" / skill
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(f"# {skill}")

        dest_plugin = tmp_path / "dest_plugin"

        copy_plugin(str(src_plugin), str(dest_plugin), "include", {"skill-a", "skill-c"})

        # Verify only a and c exist
        assert (dest_plugin / "skills" / "skill-a" / "SKILL.md").exists()
        assert (dest_plugin / "skills" / "skill-c" / "SKILL.md").exists()
        assert not (dest_plugin / "skills" / "skill-b").exists()


class TestSyncUpstream:
    """Test upstream syncing logic."""

    def test_sync_upstream_creates_namespaced_plugins(self, tmp_path):
        """AC2.2: Plugin dirs are copied with {upstream}--{plugin} prefix."""
        # Create fake upstream structure
        clone_dir = tmp_path / "clone"
        clone_dir.mkdir()
        plugins_dir = clone_dir / "plugins"
        plugins_dir.mkdir()

        test_plugin = plugins_dir / "test-plugin"
        test_plugin.mkdir()
        (test_plugin / "plugin.json").write_text("{}")

        plugins_output_dir = tmp_path / "plugins"
        plugins_output_dir.mkdir()

        upstream = {
            "name": "myupstream",
            "repo": "https://github.com/test/repo",
            "ref": "main",
        }

        with patch("sync.clone_upstream") as mock_clone:
            with patch("sync.tempfile.mkdtemp", return_value=str(clone_dir)):
                created = sync_upstream(upstream, str(plugins_output_dir))

                assert "myupstream--test-plugin" in created
                assert (plugins_output_dir / "myupstream--test-plugin").exists()

    def test_sync_upstream_handles_clone_failure(self, tmp_path):
        """AC2.6: Clone failure logs error and returns empty list."""
        plugins_output_dir = tmp_path / "plugins"
        plugins_output_dir.mkdir()

        upstream = {
            "name": "badupstream",
            "repo": "https://github.com/bad/repo",
            "ref": "main",
        }

        with patch(
            "sync.clone_upstream", side_effect=subprocess.CalledProcessError(1, "git")
        ):
            with patch("sync.tempfile.mkdtemp", return_value=str(tmp_path / "clone")):
                (tmp_path / "clone").mkdir()
                created = sync_upstream(upstream, str(plugins_output_dir))

                assert created == []

    def test_sync_upstream_handles_no_plugins_directory(self, tmp_path):
        """AC2.7: Upstream with no plugins/ directory logs warning and skips."""
        clone_dir = tmp_path / "clone"
        clone_dir.mkdir()
        # No plugins/ directory created

        plugins_output_dir = tmp_path / "plugins"
        plugins_output_dir.mkdir()

        upstream = {
            "name": "noplugins",
            "repo": "https://github.com/test/repo",
            "ref": "main",
        }

        with patch("sync.clone_upstream"):
            with patch("sync.tempfile.mkdtemp", return_value=str(clone_dir)):
                created = sync_upstream(upstream, str(plugins_output_dir))

                assert created == []

    def test_sync_upstream_applies_skill_filtering(self, tmp_path):
        """Skill filtering is applied during copy."""
        clone_dir = tmp_path / "clone"
        clone_dir.mkdir()
        plugins_dir = clone_dir / "plugins"
        plugins_dir.mkdir()

        test_plugin = plugins_dir / "test-plugin"
        test_plugin.mkdir()
        (test_plugin / ".claude-plugin").mkdir()
        (test_plugin / ".claude-plugin" / "plugin.json").write_text("{}")
        (test_plugin / "skills").mkdir()
        (test_plugin / "skills" / "skill-a").mkdir()
        (test_plugin / "skills" / "skill-b").mkdir()

        plugins_output_dir = tmp_path / "plugins"
        plugins_output_dir.mkdir()

        upstream = {
            "name": "upstream",
            "repo": "https://github.com/test/repo",
            "ref": "main",
            "plugins": {
                "include": [{"test-plugin": {"skills": {"exclude": ["skill-b"]}}}]
            },
        }

        with patch("sync.clone_upstream"):
            with patch("sync.tempfile.mkdtemp", return_value=str(clone_dir)):
                created = sync_upstream(upstream, str(plugins_output_dir))

                assert len(created) == 1
                assert (
                    plugins_output_dir / "upstream--test-plugin" / "skills" / "skill-a"
                ).exists()
                assert not (
                    plugins_output_dir / "upstream--test-plugin" / "skills" / "skill-b"
                ).exists()

    def test_sync_upstream_cleans_up_temp_directory(self, tmp_path):
        """AC2.5: Temp directory is cleaned up in finally block."""
        clone_dir = tmp_path / "clone"
        clone_dir.mkdir()
        plugins_dir = clone_dir / "plugins"
        plugins_dir.mkdir()

        plugins_output_dir = tmp_path / "plugins"
        plugins_output_dir.mkdir()

        upstream = {
            "name": "test",
            "repo": "https://github.com/test/repo",
            "ref": "main",
        }

        cleanup_called = False

        def mock_rmtree(path):
            nonlocal cleanup_called
            cleanup_called = True

        with patch("sync.clone_upstream"):
            with patch("sync.tempfile.mkdtemp", return_value=str(clone_dir)):
                with patch("sync.shutil.rmtree", side_effect=mock_rmtree):
                    sync_upstream(upstream, str(plugins_output_dir))

                    # Verify cleanup was attempted
                    assert cleanup_called
