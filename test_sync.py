"""Unit tests for sync.py - YAML parsing and filter logic."""

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from sync import (
    clone_upstream,
    copy_plugin,
    generate_marketplace,
    load_config,
    parse_plugin_filter,
    parse_skill_filter,
    should_include_plugin,
    should_include_skill,
    sync_all,
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


class TestGenerateMarketplace:
    """Test marketplace.json generation."""

    def test_generate_marketplace_creates_valid_json(self, tmp_path):
        """AC3.1: marketplace.json is generated from plugins in plugins/ directory."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create two fake plugins
        for plugin_name in ["plugin-a", "plugin-b"]:
            plugin_dir = plugins_dir / plugin_name
            plugin_dir.mkdir()
            claude_plugin_dir = plugin_dir / ".claude-plugin"
            claude_plugin_dir.mkdir()

            plugin_json = {
                "version": "1.0.0",
                "description": f"Description for {plugin_name}",
                "author": {"name": "Test Author"},
            }
            (claude_plugin_dir / "plugin.json").write_text(json.dumps(plugin_json))

        output_file = tmp_path / "marketplace.json"

        generate_marketplace(str(plugins_dir), str(output_file))

        assert output_file.exists()
        with open(output_file) as f:
            marketplace = json.load(f)

        assert marketplace["name"] == "claude-skills-mirror"
        assert marketplace["owner"]["name"] == "Mirrored"
        assert len(marketplace["plugins"]) == 2

    def test_generate_marketplace_uses_namespaced_names(self, tmp_path):
        """AC3.2: Plugin names in marketplace.json use namespaced names."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_dir = plugins_dir / "trailofbits--git-cleanup"
        plugin_dir.mkdir()
        claude_plugin_dir = plugin_dir / ".claude-plugin"
        claude_plugin_dir.mkdir()

        plugin_json = {
            "version": "1.0.0",
            "description": "Test",
            "author": {"name": "Test"},
        }
        (claude_plugin_dir / "plugin.json").write_text(json.dumps(plugin_json))

        output_file = tmp_path / "marketplace.json"

        generate_marketplace(str(plugins_dir), str(output_file))

        with open(output_file) as f:
            marketplace = json.load(f)

        assert marketplace["plugins"][0]["name"] == "trailofbits--git-cleanup"

    def test_generate_marketplace_source_paths(self, tmp_path):
        """AC3.3: marketplace.json source paths point to correct relative plugin directories."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_dir = plugins_dir / "trailofbits--foo"
        plugin_dir.mkdir()
        claude_plugin_dir = plugin_dir / ".claude-plugin"
        claude_plugin_dir.mkdir()

        plugin_json = {
            "version": "1.0.0",
            "description": "Test",
            "author": {"name": "Test"},
        }
        (claude_plugin_dir / "plugin.json").write_text(json.dumps(plugin_json))

        output_file = tmp_path / "marketplace.json"

        generate_marketplace(str(plugins_dir), str(output_file))

        with open(output_file) as f:
            marketplace = json.load(f)

        assert marketplace["plugins"][0]["source"] == "./plugins/trailofbits--foo"

    def test_generate_marketplace_includes_plugin_metadata(self, tmp_path):
        """AC3.4: marketplace.json includes correct version, description, and author."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_dir = plugins_dir / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin_dir = plugin_dir / ".claude-plugin"
        claude_plugin_dir.mkdir()

        plugin_json = {
            "version": "2.5.0",
            "description": "A test plugin for verification",
            "author": {"name": "Alice", "email": "alice@example.com"},
        }
        (claude_plugin_dir / "plugin.json").write_text(json.dumps(plugin_json))

        output_file = tmp_path / "marketplace.json"

        generate_marketplace(str(plugins_dir), str(output_file))

        with open(output_file) as f:
            marketplace = json.load(f)

        plugin_entry = marketplace["plugins"][0]
        assert plugin_entry["version"] == "2.5.0"
        assert plugin_entry["description"] == "A test plugin for verification"
        assert plugin_entry["author"]["name"] == "Alice"
        assert plugin_entry["author"]["email"] == "alice@example.com"

    def test_generate_marketplace_sorts_by_name(self, tmp_path):
        """Marketplace plugins are sorted by name."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create plugins in reverse order
        for plugin_name in ["zzz-plugin", "aaa-plugin", "mmm-plugin"]:
            plugin_dir = plugins_dir / plugin_name
            plugin_dir.mkdir()
            claude_plugin_dir = plugin_dir / ".claude-plugin"
            claude_plugin_dir.mkdir()

            plugin_json = {
                "version": "1.0.0",
                "description": f"Test {plugin_name}",
            }
            (claude_plugin_dir / "plugin.json").write_text(json.dumps(plugin_json))

        output_file = tmp_path / "marketplace.json"

        generate_marketplace(str(plugins_dir), str(output_file))

        with open(output_file) as f:
            marketplace = json.load(f)

        names = [p["name"] for p in marketplace["plugins"]]
        assert names == ["aaa-plugin", "mmm-plugin", "zzz-plugin"]

    def test_generate_marketplace_creates_output_directory(self, tmp_path):
        """generate_marketplace creates output directory if it doesn't exist."""
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        plugin_dir = plugins_dir / "test-plugin"
        plugin_dir.mkdir()
        claude_plugin_dir = plugin_dir / ".claude-plugin"
        claude_plugin_dir.mkdir()

        plugin_json = {"version": "1.0.0", "description": "Test"}
        (claude_plugin_dir / "plugin.json").write_text(json.dumps(plugin_json))

        # Output directory doesn't exist
        output_file = tmp_path / "nested" / "dir" / "marketplace.json"
        assert not output_file.parent.exists()

        generate_marketplace(str(plugins_dir), str(output_file))

        assert output_file.exists()
        assert output_file.parent.exists()


class TestSyncAll:
    """Test sync_all orchestration logic."""

    def test_sync_all_aggregates_results_from_multiple_upstreams(self, tmp_path):
        """sync_all aggregates results from multiple upstreams."""
        # Create config file
        config_file = tmp_path / "upstream.yaml"
        config_content = """
upstreams:
  - name: upstream1
    repo: https://github.com/test/repo1
    ref: main
  - name: upstream2
    repo: https://github.com/test/repo2
    ref: main
"""
        config_file.write_text(config_content)

        # Create plugins directory
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()

        # Create two temporary clone directories
        clone1_dir = tmp_path / ".tmp-clone1"
        clone1_dir.mkdir()
        plugins1 = clone1_dir / "plugins"
        plugins1.mkdir()
        plugin1_a = plugins1 / "plugin-a"
        plugin1_a.mkdir()
        (plugin1_a / "plugin.json").write_text("{}")

        clone2_dir = tmp_path / ".tmp-clone2"
        clone2_dir.mkdir()
        plugins2 = clone2_dir / "plugins"
        plugins2.mkdir()
        plugin2_b = plugins2 / "plugin-b"
        plugin2_b.mkdir()
        (plugin2_b / "plugin.json").write_text("{}")

        # Mock clone and tempfile to use our test directories
        clone_counter = [0]

        def mock_clone_upstream(repo_url, ref, dest):
            # First call gets clone1, second gets clone2
            if clone_counter[0] == 0:
                shutil.copytree(str(clone1_dir), dest)
            else:
                shutil.copytree(str(clone2_dir), dest)
            clone_counter[0] += 1

        def mock_mkdtemp(**kwargs):
            if clone_counter[0] == 0:
                return str(tmp_path / "clone1")
            else:
                return str(tmp_path / "clone2")

        with patch("sync.clone_upstream", side_effect=mock_clone_upstream):
            with patch("sync.tempfile.mkdtemp", side_effect=mock_mkdtemp):
                created = sync_all(str(config_file), str(plugins_dir))

                # Should have created plugins from both upstreams
                assert "upstream1--plugin-a" in created
                assert "upstream2--plugin-b" in created
                assert len(created) == 2

    def test_sync_all_clears_preexisting_plugins_directory(self, tmp_path):
        """sync_all clears pre-existing plugins directory content."""
        # Create config file
        config_file = tmp_path / "upstream.yaml"
        config_content = """
upstreams:
  - name: upstream
    repo: https://github.com/test/repo
    ref: main
"""
        config_file.write_text(config_content)

        # Create plugins directory with pre-existing content
        plugins_dir = tmp_path / "plugins"
        plugins_dir.mkdir()
        old_plugin_dir = plugins_dir / "old-plugin"
        old_plugin_dir.mkdir()
        (old_plugin_dir / "old-file.txt").write_text("old content")

        # Create mock clone template directory with new plugin
        clone_template = tmp_path / ".tmp-clone-template"
        clone_template.mkdir()
        plugins_src = clone_template / "plugins"
        plugins_src.mkdir()
        new_plugin = plugins_src / "new-plugin"
        new_plugin.mkdir()
        (new_plugin / "plugin.json").write_text("{}")

        clone_dirs_created = []

        def mock_mkdtemp(**kwargs):
            clone_dir = tmp_path / f".tmp-clone-{len(clone_dirs_created)}"
            clone_dir.mkdir()
            # Copy template to new location
            shutil.copytree(str(clone_template), str(clone_dir), dirs_exist_ok=True)
            clone_dirs_created.append(str(clone_dir))
            return str(clone_dir)

        with patch("sync.clone_upstream"):
            with patch("sync.tempfile.mkdtemp", side_effect=mock_mkdtemp):
                created = sync_all(str(config_file), str(plugins_dir))

                # Old plugin should be gone
                assert not (plugins_dir / "old-plugin").exists()
                # New plugin should exist
                assert (plugins_dir / "upstream--new-plugin").exists()
                # Old file should not exist
                assert not (plugins_dir / "old-plugin" / "old-file.txt").exists()
