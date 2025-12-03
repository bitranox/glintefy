"""Configuration handling for Quality sub-server.

Extracts config loading and threshold management to reduce __init__ complexity.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityThresholds:
    """Threshold values for quality analysis."""

    complexity: int = 10
    complexity_error: int = 20  # Complexity above this is error severity
    maintainability: int = 20
    maintainability_error: int = 10  # MI below this is error severity
    max_function_length: int = 50
    max_nesting_depth: int = 3
    cognitive_complexity: int = 15
    min_type_coverage: int = 80
    dead_code_confidence: int = 80
    min_docstring_coverage: int = 80
    churn_threshold: int = 20
    coupling_threshold: int = 15
    god_object_methods: int = 20
    god_object_lines: int = 500


@dataclass
class QualityFeatureFlags:
    """Feature flags for enabling/disabling analyzers."""

    type_coverage: bool = True
    dead_code_detection: bool = True
    import_cycle_detection: bool = True
    docstring_coverage: bool = True
    halstead_metrics: bool = True
    raw_metrics: bool = True
    cognitive_complexity: bool = True
    js_analysis: bool = True
    test_assertions: bool = True
    code_churn: bool = True
    beartype: bool = True
    duplication_detection: bool = True
    static_analysis: bool = True
    test_analysis: bool = True
    architecture_analysis: bool = True
    runtime_check_detection: bool = True


@dataclass
class QualityConfig:
    """Complete configuration for QualitySubServer."""

    thresholds: QualityThresholds = field(default_factory=QualityThresholds)
    features: QualityFeatureFlags = field(default_factory=QualityFeatureFlags)
    raw_config: dict[str, Any] = field(default_factory=dict)


def load_quality_config(
    config: dict[str, Any],
    complexity_threshold: int | None = None,
    maintainability_threshold: int | None = None,
    max_function_length: int | None = None,
    max_nesting_depth: int | None = None,
    cognitive_complexity_threshold: int | None = None,
) -> QualityConfig:
    """Load quality configuration from config dict with parameter overrides.

    Args:
        config: Configuration dictionary from lib_layered_config
        complexity_threshold: Override for complexity threshold
        maintainability_threshold: Override for maintainability threshold
        max_function_length: Override for max function length
        max_nesting_depth: Override for max nesting depth
        cognitive_complexity_threshold: Override for cognitive complexity

    Returns:
        QualityConfig with loaded values
    """
    thresholds = QualityThresholds(
        complexity=_get_threshold(complexity_threshold, config, "complexity_threshold", 10),
        complexity_error=config.get("complexity_error_threshold", 20),
        maintainability=_get_threshold(maintainability_threshold, config, "maintainability_threshold", 20),
        maintainability_error=config.get("maintainability_error_threshold", 10),
        max_function_length=_get_threshold(max_function_length, config, "max_function_length", 50),
        max_nesting_depth=_get_threshold(max_nesting_depth, config, "max_nesting_depth", 3),
        cognitive_complexity=_get_threshold(cognitive_complexity_threshold, config, "cognitive_complexity_threshold", 15),
        min_type_coverage=config.get("min_type_coverage", 80),
        dead_code_confidence=config.get("dead_code_confidence", 80),
        min_docstring_coverage=config.get("min_docstring_coverage", 80),
        churn_threshold=config.get("churn_threshold", 20),
        coupling_threshold=config.get("coupling_threshold", 15),
        god_object_methods=config.get("god_object_methods_threshold", 20),
        god_object_lines=config.get("god_object_lines_threshold", 500),
    )

    features = QualityFeatureFlags(
        type_coverage=config.get("enable_type_coverage", True),
        dead_code_detection=config.get("enable_dead_code_detection", True),
        import_cycle_detection=config.get("enable_import_cycle_detection", True),
        docstring_coverage=config.get("enable_docstring_coverage", True),
        halstead_metrics=config.get("enable_halstead_metrics", True),
        raw_metrics=config.get("enable_raw_metrics", True),
        cognitive_complexity=config.get("enable_cognitive_complexity", True),
        js_analysis=config.get("enable_js_analysis", True),
        test_assertions=config.get("count_test_assertions", True),
        code_churn=config.get("enable_code_churn", True),
        beartype=config.get("enable_beartype", True),
        duplication_detection=config.get("enable_duplication_detection", config.get("detect_duplication", True)),
        static_analysis=config.get("enable_static_analysis", True),
        test_analysis=config.get("enable_test_analysis", True),
        architecture_analysis=config.get("enable_architecture_analysis", True),
        runtime_check_detection=config.get("enable_runtime_check_detection", True),
    )

    return QualityConfig(thresholds=thresholds, features=features, raw_config=config)


def _get_threshold(override: int | None, config: dict[str, Any], key: str, default: int) -> int:
    """Get threshold value with override priority."""
    if override is not None:
        return override
    return config.get(key, default)


def get_analyzer_config(quality_config: QualityConfig) -> dict[str, Any]:
    """Convert QualityConfig to analyzer config dictionary."""
    t = quality_config.thresholds
    return {
        "complexity_threshold": t.complexity,
        "maintainability_threshold": t.maintainability,
        "max_function_length": t.max_function_length,
        "max_nesting_depth": t.max_nesting_depth,
        "cognitive_complexity_threshold": t.cognitive_complexity,
        "dead_code_confidence": t.dead_code_confidence,
        "churn_threshold": t.churn_threshold,
        "coupling_threshold": t.coupling_threshold,
        "god_object_methods_threshold": t.god_object_methods,
        "god_object_lines_threshold": t.god_object_lines,
    }
