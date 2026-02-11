# Codebase Linting & Quality Assessment Report

**Date**: 2026-02-11
**Scope**: `health_butler/` directory
**Tool**: `pylint 3.2.7`

---

## 📊 Executive Summary

The codebase is functionally structured but requires significant cleanup to meet Python best practices. The primary issues are related to **formatting (whitespace, line length)**, **documentation**, and **robustness (file handling, logging)**.

| Category | Severity | Occurrences | Impact |
| :--- | :--- | :--- | :--- |
| **Formatting** | Low | High (>100) | Reduces readability; irrelevant diffs in Git. |
| **Documentation** | Medium | High | Harder to onboarding new expats; unclear module purpose. |
| **Imports** | High | Moderate | Potential runtime errors; circular dependencies. |
| **Robustness** | High | Moderate | Encoding issues on non-UTF8 systems; swallowed errors. |

---

## 🔍 Detailed Module Assessment

### 1. `health_butler/swarm.py`
**Condition**: ⚠️ Needs Cleanup
*   **Whitespace**: Massive amount of trailing whitespace and line length violations.
*   **Imports**: Import errors detected (E0401) - likely path resolution issues.
*   **Logic**:
    *   `R0914`: Too many local variables in main loop.
    *   `W0718`: Catching broad `Exception` without specific handling.
    *   `W1203`: Using f-strings in logging (performance hit).
    *   `R1714`: Merge comparisons (`if x == 'a' or x == 'b'` -> `if x in ('a', 'b')`).

### 2. `health_butler/coordinator/coordinator_agent.py`
**Condition**: ⚠️ Moderate
*   **Inheritance**: `E1003`: Bad first argument to `super()` call. **Critical Fix**.
*   **Formatting**: Long lines and trailing whitespace.
*   **Documentation**: Missing module docstrings.

### 3. `health_butler/data_rag/rag_tool.py`
**Condition**: ⚠️ Moderate
*   **Error Handling**: catching broad `Exception`.
*   **Logging**: F-string interpolation in logging.
*   **Formatting**: Standard whitespace/line-length issues.

### 4. `health_butler/data_rag/ingest_usda.py`
**Condition**: ❌ Poor
*   **Indentation**: `W0311`: Bad indentation (13 spaces instead of 12). **Syntax Error Risk**.
*   **File I/O**: `W1514`: Opening files without `encoding='utf-8'`. **Platform Risk**.
*   **Complexity**: `R0914`: Too many local variables in ingestion logic.
*   **Imports**: `Wrong-import-position` for `RagTool`.

### 5. `health_butler/data_rag/download_*.py`
**Condition**: ⚠️ Needs Cleanup
*   **File I/O**: Missing encoding specification in `open()`.
*   **Imports**: `requests` imported before `pathlib` (standard lib).
*   **Formatting**: Extensive whitespace issues.

### 6. `health_butler/main.py`
**Condition**: ℹ️ Stub
*   **Imports**: Import errors detected (path issues).
*   **Structure**: Almost empty or just an entry point.

---

## 🛠 Recommended Refactoring Plan

### Phase 1: Critical Fixes (Reliability)
1.  **Fix Inheritance**: Correct `super()` calls in `coordinator_agent.py`.
2.  **Fix Indentation**: Standardize `ingest_usda.py` to 4-space indentation.
3.  **Fix File I/O**: Explicitly add `encoding='utf-8'` to all `open()` calls to prevent Windows/different locale issues.
4.  **Fix Imports**: Ensure `PYTHONPATH` is correctly set and fix relative/absolute import consistency.

### Phase 2: Code Quality (Maintainability)
5.  **Logging**: Convert `logger.info(f"...")` to `logger.info("...", args)`.
6.  **Exception Handling**: Replace `except Exception:` with specific exceptions or log the stack trace properly.
7.  **Auto-Formatting**: Run `black` or `autopep8` to instantly fix all 100+ whitespace/line-length issues.

### Phase 3: Documentation
8.  Add module-level docstrings (`"""Module description"""`) to all files.
9.  Add function comments for complex logic (especially in `rag_tool` and `swarm`).

---
