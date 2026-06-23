"""AST-based pure function detection.

Identifies functions that are deterministic and side-effect free,
making them candidates for caching.
"""

import ast
from pathlib import Path

from glintefy.subservers.review.cache.cache_models import ExistingCacheCandidate, PureFunctionCandidate


class PureFunctionDetector:
    """Detect pure functions using AST analysis."""

    # Disqualifying patterns
    IO_OPERATIONS = {"print", "open", "input", "write", "read", "execute", "compile"}
    NON_DETERMINISTIC = {"now", "today", "random", "randint", "uuid", "uuid4", "choice", "shuffle"}

    def analyze_file(self, file_path: Path) -> tuple[list[PureFunctionCandidate], list[ExistingCacheCandidate]]:
        """Analyze a single Python file for pure functions and existing caches.

        Args:
            file_path: Path to Python file

        Returns:
            Tuple of (new_candidates, existing_caches)
        """
        try:
            content = file_path.read_text()
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return ([], [])

        new_candidates = []
        existing_caches = []

        # Get module path for importing
        module_path = self._get_module_path(file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if already has cache decorator
                cache_maxsize = self._get_cache_maxsize(node)
                if cache_maxsize is not None:
                    # Found existing cache - collect it (including private methods)
                    existing_caches.append(
                        ExistingCacheCandidate(
                            file_path=file_path,
                            function_name=node.name,
                            line_number=node.lineno,
                            module_path=module_path,
                            current_maxsize=cache_maxsize,
                        )
                    )
                    continue

                # Analyze purity (including private methods - they can benefit from caching too)
                is_pure, disqualifiers = self._is_pure_function(node)

                if is_pure:
                    # Analyze expense indicators (informational, not a filter)
                    # Profiling will determine which pure functions are actually hot spots
                    indicators = self._detect_expense_indicators(node)

                    # Include ALL pure functions - let profiling decide if worth caching
                    new_candidates.append(
                        PureFunctionCandidate(
                            file_path=file_path,
                            function_name=node.name,
                            line_number=node.lineno,
                            is_pure=True,
                            expense_indicators=indicators,
                            disqualifiers=[],
                        )
                    )

        return (new_candidates, existing_caches)

    def _get_module_path(self, file_path: Path) -> str:
        """Get module import path from file path.

        Args:
            file_path: Path to Python file

        Returns:
            Module path (e.g., "package.module")
        """
        # Find src/ directory
        parts = file_path.parts
        if "src" in parts:
            idx = parts.index("src")
            module_parts = parts[idx + 1 :]
        else:
            # Fallback: use file parts
            module_parts = file_path.parts

        # Remove .py extension
        if module_parts[-1].endswith(".py"):
            module_parts = list(module_parts)
            module_parts[-1] = module_parts[-1][:-3]

        return ".".join(module_parts)

    # Cache size constants
    UNBOUNDED_CACHE = -1
    DEFAULT_LRU_MAXSIZE = 128

    def _get_cache_maxsize(self, func_node: ast.FunctionDef) -> int | None:
        """Extract maxsize from cache decorator if present.

        Args:
            func_node: Function AST node

        Returns:
            maxsize value, UNBOUNDED_CACHE for unbounded, or None if no cache
        """
        for decorator in func_node.decorator_list:
            maxsize = self._extract_maxsize_from_decorator(decorator)
            if maxsize is not None:
                return maxsize

        return None

    def _extract_maxsize_from_decorator(self, decorator: ast.expr) -> int | None:
        """Extract maxsize from a single decorator.

        Args:
            decorator: AST decorator node

        Returns:
            maxsize value or None if not a cache decorator
        """
        # @lru_cache or @cache (unbounded by default)
        if isinstance(decorator, ast.Name) and "cache" in decorator.id.lower():
            return self.UNBOUNDED_CACHE

        # @lru_cache() or @lru_cache(maxsize=X)
        if not isinstance(decorator, ast.Call):
            return None

        if not self._is_cache_call(decorator):
            return None

        return self._extract_maxsize_from_keywords(decorator.keywords)

    def _is_cache_call(self, decorator: ast.Call) -> bool:
        """Check if a Call decorator is a cache decorator.

        Args:
            decorator: AST Call node

        Returns:
            True if this is a cache decorator call
        """
        func = decorator.func

        if isinstance(func, ast.Name) and "cache" in func.id.lower():
            return True
        if isinstance(func, ast.Attribute) and "cache" in func.attr.lower():
            return True

        return False

    def _extract_maxsize_from_keywords(self, keywords: list[ast.keyword]) -> int:
        """Extract maxsize from decorator keyword arguments.

        Args:
            keywords: List of keyword arguments

        Returns:
            maxsize value (defaults to DEFAULT_LRU_MAXSIZE if not specified)
        """
        for keyword in keywords:
            if keyword.arg != "maxsize":
                continue

            if isinstance(keyword.value, ast.Constant):
                val = keyword.value.value
                # None means unbounded in lru_cache
                if val is None:
                    return self.UNBOUNDED_CACHE
                # Ensure we return an int
                return int(val) if isinstance(val, (int, float)) else self.UNBOUNDED_CACHE

            # maxsize is a variable/expression - treat as unknown (unbounded)
            return self.UNBOUNDED_CACHE

        # No maxsize specified - defaults to 128 for lru_cache
        return self.DEFAULT_LRU_MAXSIZE

    def _is_pure_function(self, func_node: ast.FunctionDef) -> tuple[bool, list[str]]:
        """Check if function is pure (deterministic, no side effects).

        Returns:
            (is_pure, disqualifiers)
        """
        disqualifiers = []

        for node in ast.walk(func_node):
            # Check for I/O operations
            if isinstance(node, ast.Call):
                if self._is_io_call(node):
                    disqualifiers.append("I/O operation")
                if self._is_non_deterministic_call(node):
                    disqualifiers.append("Non-deterministic (time/random)")

            # Check for global/nonlocal state modification
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                disqualifiers.append("Global/nonlocal state")

        return (len(disqualifiers) == 0, disqualifiers)

    def _is_io_call(self, node: ast.Call) -> bool:
        """Check if call is I/O operation."""
        if isinstance(node.func, ast.Name):
            return node.func.id in self.IO_OPERATIONS
        if isinstance(node.func, ast.Attribute):
            return node.func.attr in self.IO_OPERATIONS
        return False

    def _is_non_deterministic_call(self, node: ast.Call) -> bool:
        """Check if call is non-deterministic (time, random, etc.)."""
        if isinstance(node.func, ast.Attribute):
            return node.func.attr in self.NON_DETERMINISTIC
        if isinstance(node.func, ast.Name):
            return node.func.id in self.NON_DETERMINISTIC
        return False

    def _detect_expense_indicators(self, func_node: ast.FunctionDef) -> list[str]:
        """Detect patterns indicating computational expense."""
        indicators = []

        # Nested loops
        if self._has_nested_loops(func_node):
            indicators.append("nested_loops")

        # Recursion
        if self._is_recursive(func_node):
            indicators.append("recursion")

        # Crypto/hash operations
        if self._has_crypto_operations(func_node):
            indicators.append("crypto")

        # Complex comprehensions
        if self._has_complex_comprehensions(func_node):
            indicators.append("comprehensions")

        return indicators

    def _has_nested_loops(self, func_node: ast.FunctionDef, depth: int = 2) -> bool:
        """Check for nested loops (depth >= 2)."""
        return self._count_loop_nesting(func_node, 0) >= depth

    def _count_loop_nesting(self, node: ast.AST, current_depth: int) -> int:
        """Recursively count maximum loop nesting depth.

        Args:
            node: AST node to analyze
            current_depth: Current nesting depth

        Returns:
            Maximum nesting depth found in subtree
        """
        max_depth = current_depth

        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.For, ast.While)):
                child_depth = self._count_loop_nesting(child, current_depth + 1)
            else:
                child_depth = self._count_loop_nesting(child, current_depth)
            max_depth = max(max_depth, child_depth)

        return max_depth

    def _is_recursive(self, func_node: ast.FunctionDef) -> bool:
        """Check if function calls itself."""
        func_name = func_node.name
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == func_name:
                    return True
        return False

    def _has_crypto_operations(self, func_node: ast.FunctionDef) -> bool:
        """Check for cryptographic/hash operations."""
        crypto_keywords = ["hash", "crypt", "encrypt", "decrypt", "sha", "md5", "blake"]

        # Check function body as string
        try:
            code = ast.unparse(func_node).lower()
            return any(kw in code for kw in crypto_keywords)
        except Exception:
            return False

    def _has_complex_comprehensions(self, func_node: ast.FunctionDef) -> bool:
        """Check for complex list/dict comprehensions."""
        for node in ast.walk(func_node):
            # List/dict/set comprehensions with nested loops
            if isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp)):
                if len(node.generators) >= 2:  # Nested comprehension
                    return True
        return False
