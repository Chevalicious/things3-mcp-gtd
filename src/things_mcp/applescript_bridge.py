#!/usr/bin/env python3
import subprocess
import logging
from typing import Union, Optional, Tuple

logger = logging.getLogger(__name__)


def _run_osascript_safe(
    cmd: list, input_text: Optional[str] = None, timeout: int = 10
) -> Tuple[int, str, str]:
    """Run osascript via Popen with D-state-safe cleanup.

    When the Apple Event system is hung, osascript enters an uninterruptible
    D-state that survives SIGKILL. CPython's subprocess.run() then hangs forever
    in communicate() cleanup. This helper closes all pipes before kill and
    abandons wait() after 1 s so the calling thread always returns.

    Returns:
        (returncode, stdout, stderr) — returncode is -1 on timeout/error.
    """
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if input_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            input_bytes = input_text.encode() if input_text is not None else None
            stdout_bytes, stderr_bytes = proc.communicate(
                input=input_bytes, timeout=timeout
            )
            return proc.returncode, stdout_bytes.decode(), stderr_bytes.decode()
        except subprocess.TimeoutExpired:
            # Close pipes first — unblocks any I/O-wait in the subprocess, which
            # may let SIGKILL land. If the process is in true D-state, we abandon.
            if proc.stdin:
                try:
                    proc.stdin.close()
                except OSError:
                    pass
            if proc.stdout:
                try:
                    proc.stdout.close()
                except OSError:
                    pass
            if proc.stderr:
                try:
                    proc.stderr.close()
                except OSError:
                    pass
            proc.kill()
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass  # Process is in D-state; abandon it — do NOT block here.
            logger.error("osascript process timed out and may be in D-state (AE hung)")
            return -1, "", "D-state timeout"
    except Exception as exc:
        logger.exception("Error spawning osascript")
        return -1, "", str(exc)


def run_applescript(script: str) -> Union[str, bool]:
    """Execute a script via stdin so its text isn't passed as an argument."""
    try:
        returncode, stdout, stderr = _run_osascript_safe(
            ["/usr/bin/osascript"], input_text=script, timeout=10
        )

        if returncode != 0:
            logger.error(
                "AppleScript process returned error",
                extra={
                    "returncode": returncode,
                    "stderr_length": len(stderr),
                },
            )
            return False

        return stdout.strip()
    except Exception:
        logger.exception("Error running AppleScript")
        return False


def escape_applescript_string(text: str) -> str:
    """Escape special characters in an AppleScript string.

    Args:
        text: The string to escape

    Returns:
        The escaped string
    """
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
