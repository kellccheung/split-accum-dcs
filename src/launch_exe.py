"""Launch empty_*.exe processes in parallel for a control folder."""

from __future__ import annotations

import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, NamedTuple

logger = logging.getLogger(__name__)

# Processes still running after the row timeout. Kept alive on purpose:
# dropping the Popen object must not kill or wait for them.
_abandoned_processes: List[subprocess.Popen] = []


class ExeResult(NamedTuple):
    """Outcome of one empty_*.exe launch."""

    exe_path: Path
    returncode: int | None
    timed_out: bool


def _run_exe(exe_path: Path, timeout_minutes: float) -> ExeResult:
    logger.info("Launching %s (timeout %s minutes)", exe_path, timeout_minutes)
    try:
        # No context manager and no stdout pipe: exiting this function must not
        # kill the process or block on its output.
        proc = subprocess.Popen(
            [str(exe_path)],
            cwd=str(exe_path.parent),
        )
    except OSError as exc:
        # Placeholder/mimic files may not be valid PE binaries.
        logger.warning("Could not launch %s (%s); continuing.", exe_path.name, exc)
        return ExeResult(exe_path, -1, False)

    deadline = time.monotonic() + timeout_minutes * 60
    while True:
        returncode = proc.poll()
        if returncode is not None:
            proc.wait()
            logger.info("%s exited with code %s", exe_path.name, returncode)
            return ExeResult(exe_path, returncode, False)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            logger.error(
                "%s still running after %s minutes (pid %s); leaving it running and treating it as a failure.",
                exe_path.name,
                timeout_minutes,
                proc.pid,
            )
            _abandoned_processes.append(proc)
            return ExeResult(exe_path, None, True)

        time.sleep(min(0.5, remaining))


def launch_empty_exes(
    control_dir: Path,
    timeout_minutes: float,
    max_workers: int = 3,
) -> List[ExeResult]:
    """
    Find and launch all empty_*.exe files in control_dir in parallel.
    Wait up to timeout_minutes for each. On timeout, leave the process running.
    """
    exes = sorted(control_dir.glob("empty_*.exe"))
    if not exes:
        raise FileNotFoundError(f"No empty_*.exe found in {control_dir}")

    results: List[ExeResult] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_exe, exe, timeout_minutes): exe for exe in exes
        }
        for future in as_completed(futures):
            results.append(future.result())

    failed = [
        result.exe_path.name
        for result in results
        if not result.timed_out and result.returncode != 0
    ]
    if failed:
        logger.warning(
            "Some executables exited non-zero in %s: %s",
            control_dir,
            ", ".join(failed),
        )
    return results
