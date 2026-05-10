#!/usr/bin/env python3
import subprocess
import logging
from typing import Dict, Any, Union, Optional, Tuple

from .settings import get_settings

logger = logging.getLogger(__name__)


def _script_metadata(command: str, script: str) -> Dict[str, Any]:
    """Return metadata about an AppleScript command without exposing content."""
    return {
        "command": command,
        "line_count": len(script.splitlines()),
        "char_count": len(script),
    }


def _wrap_script_for_background(script: str) -> str:
    """Wrap AppleScript commands targeting Things3 with 'without activating' to prevent foreground activation.

    Note: 'without activating' is not valid AppleScript syntax in tell blocks, so this function
    currently returns the script unchanged. Background execution prevention would need to be
    handled at the osascript level or through other means.

    Args:
        script: The AppleScript code to potentially wrap

    Returns:
        The original script (wrapping disabled due to syntax limitations)
    """
    # Check if background execution is disabled via settings
    if get_settings().things_mcp_disable_background_osascript:
        logger.debug("Background execution disabled via settings")
        return script

    # NOTE: 'without activating' is not valid AppleScript syntax in tell blocks
    # The syntax causes errors: "Expected end of line but found 'without'"
    # For now, return the script unchanged. Background execution would need
    # to be handled differently (e.g., using osascript flags or other methods)

    # Check if script targets Things3 - log for debugging but don't modify
    if 'tell application "Things3"' in script or 'tell application "Things"' in script:
        logger.debug(
            "Script targets Things3 (background execution wrapping disabled due to syntax limitations)"
        )

    return script


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
    """Run an AppleScript command and return the result.

    Automatically wraps commands targeting Things3 with 'without activating' to prevent
    the application from appearing in the foreground, unless disabled via the
    THINGS_MCP_DISABLE_BACKGROUND_OSASCRIPT environment variable.

    Args:
        script: The AppleScript code to execute

    Returns:
        The result of the AppleScript execution, or False if it failed
    """
    try:
        # Wrap script for background execution if targeting Things3
        wrapped_script = _wrap_script_for_background(script)

        # Use stdin for multi-line scripts (osascript -e only works for single-line)
        if "\n" in wrapped_script:
            returncode, stdout, stderr = _run_osascript_safe(
                ["osascript"], input_text=wrapped_script, timeout=10
            )
        else:
            returncode, stdout, stderr = _run_osascript_safe(
                ["osascript", "-e", wrapped_script], timeout=10
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
    if not text:
        return ""

    # Replace any "+" with spaces first
    text = text.replace("+", " ")

    # Escape quotes by doubling them (AppleScript style)
    return text.replace('"', '""')
