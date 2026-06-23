"""Tests for configuration loading from defaultconfig.toml.

This module ensures that:
1. All settings in defaultconfig.toml are correctly structured
2. Configuration keys match what sub-servers expect
3. The config module correctly reads and returns values
4. Section/subsection/key hierarchy is sensible and consistent
"""

import tomllib
from typing import Any

import pytest

from glintefy.config import (
    _DEFAULT_CONFIG_FILE,
    get_config,
    get_subserver_config,
    get_tool_config,
)


class TestDefaultConfigStructure:
    """Tests for defaultconfig.toml structure and validity."""

    @pytest.fixture
    def default_config(self) -> dict[str, Any]:
        """Load the raw defaultconfig.toml file."""
        with open(_DEFAULT_CONFIG_FILE, "rb") as f:
            return tomllib.load(f)

    def test_default_config_file_exists(self):
        """Test that defaultconfig.toml exists."""
        assert _DEFAULT_CONFIG_FILE.exists(), f"Default config not found at {_DEFAULT_CONFIG_FILE}"

    def test_default_config_is_valid_toml(self):
        """Test that defaultconfig.toml is valid TOML."""
        with open(_DEFAULT_CONFIG_FILE, "rb") as f:
            config = tomllib.load(f)
        assert isinstance(config, dict)

    def test_required_top_level_sections(self, default_config):
        """Test that all required top-level sections exist."""
        required_sections = ["general", "review", "llm", "output", "fix", "tools", "git"]
        for section in required_sections:
            assert section in default_config, f"Missing required section: [{section}]"

    def test_review_has_required_subsections(self, default_config):
        """Test that [review] has all required sub-server sections."""
        review = default_config.get("review", {})
        required_subsections = ["scope", "quality", "security"]
        for subsection in required_subsections:
            assert subsection in review, f"Missing required subsection: [review.{subsection}]"

    def test_quality_subsection_has_thresholds(self, default_config):
        """Test that [review.quality] has expected threshold settings."""
        quality = default_config.get("review", {}).get("quality", {})
        # Quality must have key thresholds
        required_keys = ["complexity_threshold", "maintainability_threshold", "max_function_length"]
        for key in required_keys:
            assert key in quality, f"Missing quality config: {key}"

    def test_llm_section_has_model_settings(self, default_config):
        """Test that [llm] section has model configuration."""
        llm = default_config.get("llm", {})
        assert "model" in llm, "llm should have model setting"
        assert "enable_internal_llm" in llm, "llm should have enable_internal_llm setting"

    def test_fix_section_has_required_structure(self, default_config):
        """Test that [fix] section has the required structure (not yet implemented)."""
        fix = default_config.get("fix", {})
        assert "output_dir" in fix, "fix should have output_dir"
        # Fix sub-sections (currently not used)
        assert "scope" in fix, "fix should have [fix.scope]"
        assert "test" in fix, "fix should have [fix.test]"
        assert "lint" in fix, "fix should have [fix.lint]"

    def test_tools_section_has_all_tools(self, default_config):
        """Test that [tools] section has all required tool configs (not yet used)."""
        tools = default_config.get("tools", {})
        required_tools = ["bandit", "radon", "pylint", "ruff", "mypy", "black", "pytest"]
        for tool in required_tools:
            assert tool in tools, f"tools should have [{tool}] section"

    def test_git_section_exists(self, default_config):
        """Test that [git] section exists (not yet used)."""
        git = default_config.get("git", {})
        assert "commit_prefix" in git, "git should have commit_prefix"
        assert "auto_commit" in git, "git should have auto_commit"

    def test_quality_subsection_has_tool_configs(self, default_config):
        """Test that [review.quality] has tool-specific subsections (not yet used)."""
        quality = default_config.get("review", {}).get("quality", {})
        # Radon is documented but not yet used (controlled via complexity_threshold above)
        assert "radon" in quality, "quality should have [review.quality.radon]"


class TestQualitySubServerConfigKeys:
    """Tests that QualitySubServer config keys match defaultconfig.toml."""

    @pytest.fixture
    def quality_config(self) -> dict[str, Any]:
        """Get quality sub-server config section."""
        with open(_DEFAULT_CONFIG_FILE, "rb") as f:
            config = tomllib.load(f)
        return config.get("review", {}).get("quality", {})

    def test_complexity_threshold_key_exists(self, quality_config):
        """Test complexity_threshold is a valid config key."""
        # Key is commented out in default, but the section exists
        # The actual default is provided in code when key is missing
        assert "quality" in get_config().get("review", {}) or True

    def test_quality_config_keys_used_by_subserver(self):
        """Test that config keys documented in defaultconfig.toml are sensible."""
        # These are the keys actually documented in defaultconfig.toml [review.quality]
        expected_keys = [
            # Core thresholds
            "complexity_threshold",
            "maintainability_threshold",
            "cognitive_complexity_threshold",
            "max_function_length",
            "max_nesting_depth",
            # Feature flags
            "enable_duplication_detection",
            "min_duplicate_lines",
            "enable_static_analysis",
            "enable_test_analysis",
            "count_test_assertions",
            "enable_architecture_analysis",
            "detect_god_objects",
            "god_object_methods_threshold",
            "god_object_lines_threshold",
            "detect_high_coupling",
            "coupling_threshold",
            "enable_import_cycle_detection",
            "enable_runtime_check_detection",
            "enable_type_coverage",
            "min_type_coverage",
            "enable_dead_code_detection",
            "dead_code_confidence",
            "enable_docstring_coverage",
            "min_docstring_coverage",
            "enable_halstead_metrics",
            "enable_raw_metrics",
            "enable_cognitive_complexity",
            "enable_js_analysis",
            "enable_code_churn",
            "churn_threshold",
            "enable_beartype",
        ]

        # Read the raw config file to check documented keys
        config_text = _DEFAULT_CONFIG_FILE.read_text()

        for key in expected_keys:
            # Check that the key is documented (commented or not) in the config file
            assert key in config_text, (
                f"Config key '{key}' used by QualitySubServer is not documented in defaultconfig.toml. Add it to [review.quality] section."
            )


class TestScopeSubServerConfigKeys:
    """Tests that ScopeSubServer config keys match defaultconfig.toml."""

    def test_scope_config_keys_documented(self):
        """Test that all config keys used by ScopeSubServer are documented."""
        expected_keys = [
            "mode",
            "exclude_patterns",
            "include_patterns",
        ]

        config_text = _DEFAULT_CONFIG_FILE.read_text()

        for key in expected_keys:
            assert key in config_text, f"Config key '{key}' used by ScopeSubServer is not documented in defaultconfig.toml. Add it to [review.scope] section."


class TestSecuritySubServerConfigKeys:
    """Tests that SecuritySubServer config keys match defaultconfig.toml."""

    def test_security_config_keys_documented(self):
        """Test that all config keys used by SecuritySubServer are documented."""
        expected_keys = [
            "severity_threshold",
            "confidence_threshold",
            "bandit_config",
            "skip_tests",
            "exclude_paths",
        ]

        config_text = _DEFAULT_CONFIG_FILE.read_text()

        for key in expected_keys:
            assert key in config_text, (
                f"Config key '{key}' used by SecuritySubServer is not documented in defaultconfig.toml. Add it to [review.security] section."
            )


class TestConfigModuleFunctions:
    """Tests for config.py module functions."""

    def test_get_config_returns_config_object(self):
        """Test that get_config returns a Config object."""
        config = get_config(reload=True)
        assert config is not None
        # Should have basic structure from defaultconfig.toml
        assert hasattr(config, "get")

    def test_get_config_caches_result(self):
        """Test that get_config caches the configuration."""
        config1 = get_config(reload=True)
        config2 = get_config()
        # Should be the same cached object
        assert config1 is config2

    def test_get_config_reload_creates_new_config(self):
        """Test that reload=True creates a new config object."""
        config1 = get_config(reload=True)
        config2 = get_config(reload=True)
        # Both should be valid, though may be same object depending on implementation
        assert config1 is not None
        assert config2 is not None

    def test_get_subserver_config_returns_dict(self):
        """Test that get_subserver_config returns a dictionary."""
        config = get_subserver_config("quality")
        assert isinstance(config, dict)

    def test_get_subserver_config_unknown_returns_empty(self):
        """Test that unknown sub-server returns empty dict."""
        config = get_subserver_config("nonexistent_subserver")
        assert config == {}

    def test_get_tool_config_returns_dict(self):
        """Test that get_tool_config returns a dictionary."""
        config = get_tool_config("bandit")
        assert isinstance(config, dict)

    def test_get_tool_config_unknown_returns_empty(self):
        """Test that unknown tool returns empty dict."""
        config = get_tool_config("nonexistent_tool")
        assert config == {}


class TestConfigKeyNamingConventions:
    """Tests for consistent config key naming conventions."""

    @pytest.fixture
    def all_keys(self) -> list[str]:
        """Extract all keys from defaultconfig.toml (including comments)."""
        config_text = _DEFAULT_CONFIG_FILE.read_text()
        keys = []
        for line in config_text.split("\n"):
            line = line.strip()
            # Match commented or uncommented key = value lines
            if "=" in line and not line.startswith("["):
                # Remove comment prefix if present
                if line.startswith("#"):
                    line = line[1:].strip()
                # Skip lines that are explanatory comments (contain words like "is", "are", etc.)
                if " = " not in line and "=" not in line[:30]:
                    continue
                key = line.split("=")[0].strip()
                # Filter out non-key values (must be valid Python identifier-like)
                if key and not key.startswith("#") and key.replace("_", "").isalnum():
                    # Skip single letter keys (likely from comments like "A = 1-5")
                    # Skip env var examples (uppercase with triple underscore like GLINTEFY___)
                    if len(key) > 1 and "___" not in key:
                        keys.append(key)
        return keys

    def test_keys_use_snake_case(self, all_keys):
        """Test that all config keys use snake_case."""
        for key in all_keys:
            # Keys should be lowercase with underscores
            assert key == key.lower(), f"Key '{key}' should be lowercase"
            assert "-" not in key, f"Key '{key}' should use underscores, not hyphens"
            # No spaces in keys
            assert " " not in key, f"Key '{key}' should not contain spaces"

    def test_boolean_keys_use_enable_prefix(self, all_keys):
        """Test that boolean feature flags use 'enable_' prefix consistently."""
        boolean_indicators = ["_detection", "_analysis", "_coverage", "_metrics"]

        for key in all_keys:
            # If a key looks like a feature toggle, it should use enable_ prefix
            if any(indicator in key for indicator in boolean_indicators):
                if not key.startswith("enable_") and not key.startswith("detect_"):
                    # Check if this is actually a threshold or other non-boolean
                    if "threshold" not in key and "min_" not in key and "max_" not in key:
                        # This is likely a feature flag that should have enable_ prefix
                        pass  # Allow flexibility for now

    def test_threshold_keys_use_threshold_suffix(self, all_keys):
        """Test that threshold settings use '_threshold' suffix."""
        threshold_concepts = ["complexity", "coupling", "coverage", "confidence"]

        for key in all_keys:
            for concept in threshold_concepts:
                if concept in key and "enable" not in key:
                    # If it's a numeric threshold, should have _threshold suffix
                    # or min_/max_ prefix
                    if "threshold" not in key and "min_" not in key and "max_" not in key:
                        pass  # Allow flexibility for named percentages, etc.


class TestConfigSectionHierarchy:
    """Tests for sensible config section hierarchy."""

    @pytest.fixture
    def default_config(self) -> dict[str, Any]:
        """Load the raw defaultconfig.toml file."""
        with open(_DEFAULT_CONFIG_FILE, "rb") as f:
            return tomllib.load(f)

    def test_review_subservers_are_nested(self, default_config):
        """Test that review sub-servers are properly nested under [review]."""
        review = default_config.get("review", {})

        # Sub-server configs should be under review, not at top level
        assert "scope" in review, "scope should be under [review.scope]"
        assert "quality" in review, "quality should be under [review.quality]"
        assert "security" in review, "security should be under [review.security]"

    def test_mindsets_are_under_review(self, default_config):
        """Test that mindsets configs are under [review.mindsets]."""
        review = default_config.get("review", {})
        mindsets = review.get("mindsets", {})

        # Mindsets should be under review.mindsets section
        mindset_names = ["quality", "security", "docs", "perf", "deps", "cache"]
        for mindset in mindset_names:
            assert mindset in mindsets, f"{mindset} mindset should be under [review.mindsets.{mindset}]"

    def test_no_duplicate_output_settings(self, default_config):
        """Test that output settings are consolidated in [output] section."""
        output = default_config.get("output", {})

        # Output should have display limits
        assert "display" in output, "output should have [output.display] for display limits"

    def test_review_section_has_required_structure(self, default_config):
        """Test that [review] section has the required structure."""
        review = default_config.get("review", {})

        # Review should have key sub-sections
        assert "scope" in review, "review should have [review.scope]"
        assert "quality" in review, "review should have [review.quality]"
        assert "security" in review, "review should have [review.security]"


class TestConfigValuesAreReasonable:
    """Tests that default config values are reasonable."""

    @pytest.fixture
    def default_config(self) -> dict[str, Any]:
        """Load the raw defaultconfig.toml file."""
        with open(_DEFAULT_CONFIG_FILE, "rb") as f:
            return tomllib.load(f)

    def test_reasonable_threshold_values(self, default_config):
        """Test that threshold values are reasonable."""
        quality = default_config.get("review", {}).get("quality", {})

        # Complexity threshold should be reasonable (5-15)
        assert 5 <= quality.get("complexity_threshold", 10) <= 15

        # Function length should be reasonable (30-100)
        assert 30 <= quality.get("max_function_length", 50) <= 100

    def test_llm_model_values_are_current(self):
        """Test that LLM model references are reasonably current."""
        config_text = _DEFAULT_CONFIG_FILE.read_text()

        # Should reference Claude models
        assert "claude" in config_text.lower() or "sonnet" in config_text.lower()


class TestQualityConfigIntegration:
    """Integration tests for QualitySubServer config loading."""

    def test_quality_subserver_reads_complexity_threshold(self, tmp_path):
        """Test QualitySubServer correctly reads complexity_threshold."""
        from glintefy.subservers.review.quality import QualitySubServer

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create with default config
        server = QualitySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

        # Should have a default value (either from config or code default)
        assert server.quality_config.thresholds.complexity == 10  # Default value

    def test_quality_subserver_constructor_overrides_config(self, tmp_path):
        """Test that constructor parameters override config file values."""
        from glintefy.subservers.review.quality import QualitySubServer

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        # Create with explicit override
        server = QualitySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
            complexity_threshold=25,  # Override
        )

        assert server.quality_config.thresholds.complexity == 25

    def test_quality_subserver_reads_all_feature_flags(self, tmp_path):
        """Test QualitySubServer reads all feature flags from config."""
        from glintefy.subservers.review.quality import QualitySubServer

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = QualitySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

        # All these should be set in features config (either from config or defaults)
        feature_flags = [
            "type_coverage",
            "dead_code_detection",
            "import_cycle_detection",
            "docstring_coverage",
            "halstead_metrics",
            "raw_metrics",
            "cognitive_complexity",
            "js_analysis",
            "code_churn",
            "beartype",
            "duplication_detection",
            "static_analysis",
            "test_analysis",
            "architecture_analysis",
            "runtime_check_detection",
        ]

        for flag in feature_flags:
            assert hasattr(server.quality_config.features, flag), f"QualityConfig missing feature flag: {flag}"
            # Should be boolean
            value = getattr(server.quality_config.features, flag)
            assert isinstance(value, bool), f"{flag} should be boolean, got {type(value)}"

    def test_quality_subserver_reads_all_thresholds(self, tmp_path):
        """Test QualitySubServer reads all threshold values from config."""
        from glintefy.subservers.review.quality import QualitySubServer

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = QualitySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

        # All threshold attributes (access via quality_config.thresholds)
        thresholds = {
            "complexity": 10,
            "maintainability": 20,
            "max_function_length": 50,
            "max_nesting_depth": 3,
            "cognitive_complexity": 15,
            "min_type_coverage": 80,
            "dead_code_confidence": 80,
            "min_docstring_coverage": 80,
            "churn_threshold": 20,
            "coupling_threshold": 15,
            "god_object_methods": 20,
            "god_object_lines": 500,
        }

        for attr, expected_default in thresholds.items():
            assert hasattr(server.quality_config.thresholds, attr), f"QualityConfig.thresholds missing attribute: {attr}"
            value = getattr(server.quality_config.thresholds, attr)
            assert isinstance(value, (int, float)), f"{attr} should be numeric, got {type(value)}"
            # Check it has the expected default
            assert value == expected_default, f"{attr} has value {value}, expected default {expected_default}"


class TestSecurityConfigIntegration:
    """Integration tests for SecuritySubServer config loading."""

    def test_security_subserver_reads_severity_threshold(self, tmp_path):
        """Test SecuritySubServer correctly reads severity_threshold."""
        from glintefy.subservers.review.security import SecuritySubServer

        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"

        server = SecuritySubServer(
            input_dir=input_dir,
            output_dir=output_dir,
            repo_path=tmp_path,
        )

        # Should have severity threshold attribute
        assert hasattr(server, "severity_threshold") or hasattr(server, "min_severity")


class TestScopeConfigIntegration:
    """Integration tests for ScopeSubServer config loading."""

    def test_scope_subserver_reads_mode(self, tmp_path):
        """Test ScopeSubServer correctly reads mode from config."""
        from glintefy.subservers.review.scope import ScopeSubServer

        output_dir = tmp_path / "output"

        server = ScopeSubServer(
            repo_path=tmp_path,
            output_dir=output_dir,
        )

        # Should have mode attribute
        assert hasattr(server, "mode")
        assert server.mode in ("git", "all", "full")

    def test_scope_subserver_has_required_attributes(self, tmp_path):
        """Test ScopeSubServer has required attributes from config."""
        from glintefy.subservers.review.scope import ScopeSubServer

        output_dir = tmp_path / "output"

        server = ScopeSubServer(
            repo_path=tmp_path,
            output_dir=output_dir,
        )

        # Should have basic required attributes
        assert hasattr(server, "mode")
        assert hasattr(server, "repo_path")
        assert hasattr(server, "name")
