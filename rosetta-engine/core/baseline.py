import json
import os
import shlex
import subprocess
from typing import Any


class BaselineError(RuntimeError):
    pass


def execute_legacy_baseline(command: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    """Run an external legacy adapter using JSON on stdin and stdout."""
    if not command:
        raise BaselineError("Legacy baseline command is required for java_executed mode.")

    argv = shlex.split(command, posix=os.name != "nt")
    if not argv:
        raise BaselineError("Legacy baseline command is empty.")

    completed = subprocess.run(
        argv,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise BaselineError(f"Legacy baseline command failed ({completed.returncode}): {detail}")

    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise BaselineError("Legacy baseline command did not return valid JSON.") from exc

    if not isinstance(result, dict):
        raise BaselineError("Legacy baseline output must be a JSON object.")
    return result