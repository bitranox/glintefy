# Feature Documentation: CLI Behavior Scaffold

## Status

Complete

## Links & References
**Feature Requirements:** Scaffold requirements (ad-hoc)
**Task/Ticket:** None documented
**Pull Requests:** Pending current refactor
**Related Files:**

* src/glintefy/behaviors.py
* src/glintefy/cli.py
* src/glintefy/__main__.py
* src/glintefy/__init__.py
* src/glintefy/__init__conf__.py
* tests/test_cli.py
* tests/test_module_entry.py
* tests/test_behaviors.py
* tests/test_scripts.py

---

## Problem Statement

The original scaffold concentrated the greeting, failure trigger, and CLI
orchestration inside a single module, making it harder to explain module intent
and to guarantee that the console script and ``python -m`` execution paths stay
behaviourally identical. We needed clearer module boundaries and shared helpers
for traceback preferences without introducing the full domain/application
separation that would be overkill for this minimal template.

## Solution Overview

* Extracted the behaviour helpers into ``behaviors.py`` so both CLI and library
  consumers have a single cohesive module documenting the temporary domain.
* Simplified ``cli.py`` to import the behaviour helpers, added explicit
  functions for applying and restoring traceback preferences, and centralised
  the exit-code handling used by both entry points.
* Reduced ``__main__.py`` to a thin wrapper delegating to the CLI helper while
  sharing the same traceback state restoration helpers.
* Re-exported the helpers through ``__init__.py`` so CLI and library imports
  draw from the same source.
* Documented the responsibilities in this module reference so future refactors
  have an authoritative baseline.

---

## Architecture Integration

**App Layer Fit:** This package remains a CLI-first utility; all modules live in
the transport/adapter layer, with ``behaviors.py`` representing the small
stand-in domain.

**Data Flow:**
1. CLI parses options with rich-click.
2. Rich traceback is installed when ``--traceback`` flag is provided.
3. Commands delegate to behaviour helpers.
4. Exit codes and exceptions are handled by Click and Rich.

**System Dependencies:**
* ``rich_click`` for CLI UX with beautiful output
* ``rich`` for enhanced tracebacks and console output
* ``importlib.metadata`` via ``__init__conf__`` to present package metadata

---

## Core Components

### behaviors.emit_greeting

* **Purpose:** Write the canonical greeting used in smoke tests and
  documentation.
* **Input:** Optional text stream (defaults to ``sys.stdout``).
* **Output:** Writes ``"Hello World\n"`` to the stream and flushes if possible.
* **Location:** src/glintefy/behaviors.py

### behaviors.raise_intentional_failure

* **Purpose:** Provide a deterministic failure hook for error-handling tests.
* **Input:** None.
* **Output:** Raises ``RuntimeError('I should fail')``.
* **Location:** src/glintefy/behaviors.py

### behaviors.noop_main

* **Purpose:** Placeholder entry for transports expecting a ``main`` callable.
* **Input:** None.
* **Output:** Returns ``None``.
* **Location:** src/glintefy/behaviors.py

### cli.apply_traceback_preferences

* **Purpose:** Synchronise traceback configuration between the CLI and ``python -m`` paths.
* **Input:** Boolean flag enabling rich tracebacks.
* **Output:** Installs rich traceback handler with show_locals=True.
* **Location:** src/glintefy/cli.py

### cli.main

* **Purpose:** Execute the click command group with shared exit handling.
* **Input:** Optional argv, restore flag, summary and verbose limits.
* **Output:** Integer exit code (0 on success, mapped error codes otherwise).
* **Location:** src/glintefy/cli.py

### cli.cli_info / cli.cli_hello / cli.cli_fail

* **Purpose:** Subcommands for displaying metadata, greeting, and triggering
  intentional failures for testing error handling.
* **Input:** None (commands receive Click context automatically).
* **Output:** None (execute their respective behaviors).
* **Location:** src/glintefy/cli.py

### cli.main

* **Purpose:** Entry point for console scripts and module execution, handling
  exit codes and exception propagation.
* **Input:** Optional argv and standalone_mode flag.
* **Output:** Integer exit code (0 for success, non-zero for errors).
* **Location:** src/glintefy/cli.py

### __main__

* **Purpose:** Provide ``python -m glintefy`` entry point by
  delegating directly to ``cli.main()``.
* **Input:** None (reads from sys.argv).
* **Output:** System exit with code from ``cli.main()``.

### __init__conf__.print_info

* **Purpose:** Render the statically-defined project metadata for the CLI ``info`` command.
* **Input:** None.
* **Output:** Writes the hard-coded metadata block to ``stdout``.
* **Location:** src/glintefy/__init__conf__.py

### Package Exports

* ``__init__.py`` re-exports behaviour helpers and ``print_info`` for library
  consumers. No legacy compatibility layer remains; new code should import from
  the canonical module paths.

---

## Implementation Details

**Dependencies:**

* External: ``rich_click``, ``rich`` (for Console and traceback)
* Internal: ``behaviors`` module, ``__init__conf__`` static metadata constants

**Key Configuration:**

* No environment variables required.
* Traceback preferences controlled via CLI ``--traceback`` flag.

**Database Changes:**

* None.

**Error Handling Strategy:**

* Rich tracebacks are installed when ``--traceback`` flag is provided.
* Click's built-in exception handling is used with standalone_mode.
* Exit codes are returned via SystemExit for proper shell integration.

---

## Testing Approach

**Manual Testing Steps:**

1. ``glintefy`` → prints CLI help (no default action).
2. ``glintefy hello`` → prints greeting.
3. ``glintefy fail`` → prints truncated traceback.
4. ``glintefy --traceback fail`` → prints full rich traceback.
5. ``python -m glintefy --traceback fail`` → matches console output.

**Automated Tests:**

* ``tests/test_cli.py`` exercises the help-first behaviour, failure path,
  metadata output, and invalid command handling for the click surface.
* ``tests/test_module_entry.py`` ensures ``python -m`` entry mirrors the console
  script, including traceback behaviour.
* ``tests/test_behaviors.py`` verifies greeting/failure helpers against custom
  streams.
* ``tests/test_scripts.py`` validates the automation entry points via the shared
  scripts CLI.
* ``tests/test_cli.py`` and ``tests/test_module_entry.py`` now introduce
  structured recording helpers (``CapturedRun`` and ``PrintedTraceback``) so the
  assertions read like documented scenarios.
* Doctests embedded in behaviour and CLI helpers provide micro-regression tests
  for argument handling.

**Edge Cases:**

* Running without subcommand delegates to ``noop_main`` (no output).
* Repeated invocations respect previous traceback preference thanks to
  restoration helpers.

**Test Data:**

* No fixtures required; tests rely on built-in `CliRunner` and monkeypatching.

---

## Known Issues & Future Improvements

**Current Limitations:**

* Behaviour module still contains placeholder logic; real logging helpers will
  replace it in future iterations.

**Future Enhancements:**

* Introduce structured logging once the logging stack lands.
* Expand the module reference when new commands or behaviours are added.

---

## Risks & Considerations

**Technical Risks:**

* Traceback formatting depends on Rich's traceback module; updates may change
  the appearance of error output.

**User Impact:**

* None expected; CLI surface and public imports remain backward compatible.

---

## Documentation & Resources

**Internal References:**

* README.md – usage examples
* INSTALL.md – installation options
* DEVELOPMENT.md – developer workflow

**External References:**

* rich-click documentation: https://github.com/ewels/rich-click
* rich documentation: https://rich.readthedocs.io/

---

**Created:** 2025-09-26 by Codex (automation)
**Last Updated:** 2025-09-26 by Codex
**Review Cycle:** Evaluate during next logging feature milestone

---

## Instructions for Use

1. Trigger this document whenever CLI behaviour helpers change.
2. Keep module descriptions in sync with code during future refactors.
3. Extend with new components when additional commands or behaviours ship.
