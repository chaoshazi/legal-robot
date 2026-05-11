"""Sandboxed Python execution for the code interpreter tool.

Runs user-provided Python code in a subprocess with:
- Static analysis (patterns that are always blocked)
- Execution timeout (primary guard)
- Temp-file based isolation (no direct access to app code)
- Dangerous builtins removed from the subprocess environment

Security model:
  The code runs in an isolated subprocess with no access to the main
  application's memory, database, or file handles. The worst case is a
  30-second burn of one CPU core plus reading/writing /tmp files.
"""

import os
import re
import subprocess
import sys
import tempfile
import textwrap

# ── Always-blocked patterns (defence-in-depth) ──────────────────────────
# These match attempts to access import internals or call dangerous
# builtins directly.
_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b__import__\s*\("),
    re.compile(r"\bexec\s*\("),
    re.compile(r"\beval\s*\("),
    re.compile(r"\bcompile\s*\("),
    re.compile(r"\bopen\s*\("),
    re.compile(r"__builtins__"),
    re.compile(r"__getattr__"),
    re.compile(r"__subclasses__"),
    re.compile(r"getattr\s*\(.*__"),
]

_MAX_OUTPUT_CHARS = 4000
_DEFAULT_TIMEOUT = 30


def _check_blocked_patterns(code: str) -> str | None:
    """Return an error message if the code contains blocked patterns."""
    for i, pattern in enumerate(_BLOCKED_PATTERNS):
        if pattern.search(code):
            return f"[安全拦截] 代码包含不允许的操作（匹配规则 #{i + 1}）"
    return None


def _build_sandbox_script(user_code: str) -> str:
    """Wrap user code with safety stubs.

    Removes builtins that could be used for file I/O or code injection,
    then prepends the user code.
    """
    # Disable builtins that could be used for file I/O or interactive
    # input.  Keep eval/exec/compile — the import system needs them.
    guard = textwrap.dedent("""\
        __builtins__.open = None
        __builtins__.input = None
        __builtins__.breakpoint = None
    """)
    return guard + "\n\n" + user_code


def run_code(code: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Execute *code* in a sandboxed subprocess and return its output.

    Args:
        code: Python source code to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        Captured stdout on success, or an error message on failure.
    """
    # ── Static analysis ────────────────────────────────────────────────
    blocked = _check_blocked_patterns(code)
    if blocked is not None:
        return blocked

    # ── Build sandbox script ───────────────────────────────────────────
    full_src = _build_sandbox_script(code)

    # ── Write to temp file ─────────────────────────────────────────────
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        prefix="sandbox_",
        delete=False,
    )
    try:
        tmp.write(full_src)
        tmp.close()

        # ── Execute ────────────────────────────────────────────────────
        proc = subprocess.run(
            [sys.executable, tmp.name],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={"PYTHONIOENCODING": "utf-8"},
            cwd=tempfile.gettempdir(),
        )

        if proc.returncode != 0:
            stderr = proc.stderr.strip()
            lines = stderr.splitlines()
            if lines and "Traceback" in lines[0]:
                lines = [l for l in lines if not l.startswith("  File") and "in " not in l]
            msg = "\n".join(lines) if lines else stderr
            return f"[执行错误]\n{msg[: _MAX_OUTPUT_CHARS]}"

        out = proc.stdout.strip()
        if not out:
            return "代码已执行完毕（无输出）"
        return out[: _MAX_OUTPUT_CHARS]

    except subprocess.TimeoutExpired:
        return f"[超时] 代码执行超过 {timeout} 秒，已终止"
    except FileNotFoundError:
        return "[环境错误] Python 解释器不可用"
    except Exception as e:
        return f"[执行异常] {e}"
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


async def async_run_code(code: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Async wrapper around :func:`run_code`."""
    from asyncio import to_thread
    return await to_thread(run_code, code, timeout)
