"""DCS run automation entry point."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# Allow `python src\main.py` without installing a package.
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aggregate import aggregate_results, ensure_mimic_results  # noqa: E402
from config_loader import RunConfig, load_run_configs  # noqa: E402
from launch_exe import launch_empty_exes  # noqa: E402
from prepare_run import prepare_control_folder  # noqa: E402

logger = logging.getLogger("dcs_automation")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def configure_logging(verbose: bool, log_file: Path | None = None) -> Path:
    """Configure console + file logging. Returns the log file path used."""
    level = logging.DEBUG if verbose else logging.INFO
    root = project_root()
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    if log_file is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"dcs_run_{stamp}.log"
    else:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return log_file.resolve()


def process_run(root: Path, run: RunConfig) -> bool:
    """Run one Excel row. Returns False when the row times out."""
    logger.info(
        "Starting run row %s: dcs_folder=%s control_folder=%s timeout_minutes=%s",
        run.row_number,
        run.dcs_folder,
        run.control_folder,
        run.timeout_minutes,
    )
    control_dir = prepare_control_folder(root, run)
    results = launch_empty_exes(control_dir, timeout_minutes=run.timeout_minutes)
    if any(result.timed_out for result in results):
        logger.error(
            "Run row %s (%s) timed out after %s minutes; leaving the executable running and skipping aggregation.",
            run.row_number,
            run.dcs_folder,
            run.timeout_minutes,
        )
        return False

    dcs_dir = (root / run.dcs_folder).resolve()
    ensure_mimic_results(dcs_dir, control_dir)
    output_dir = aggregate_results(dcs_dir, control_dir)
    logger.info("Aggregate output written to %s", output_dir)
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Automate DCS split runs from Excel config.")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to Excel config workbook (.xlsx)",
    )
    parser.add_argument(
        "--sheet",
        default="runs",
        help="Excel sheet name (default: runs)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional path for the log file (default: logs/dcs_run_YYYYMMDD_HHMMSS.log)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)

    log_path = Path(args.log_file) if args.log_file else None
    if log_path is not None and not log_path.is_absolute():
        log_path = (project_root() / log_path).resolve()

    log_file = configure_logging(args.verbose, log_file=log_path)

    root = project_root()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (root / config_path).resolve()

    logger.info("Log file: %s", log_file)
    logger.info("Project root: %s", root)
    logger.info("Loading config: %s", config_path)

    try:
        runs = load_run_configs(config_path, sheet_name=args.sheet)
    except Exception as exc:
        logger.error("Failed to load config: %s", exc)
        print(f"\nLog saved to: {log_file}", flush=True)
        return 1

    failures = 0
    for run in runs:
        try:
            if not process_run(root, run):
                failures += 1
        except Exception as exc:
            failures += 1
            logger.exception(
                "Run row %s (%s) failed: %s",
                run.row_number,
                run.dcs_folder,
                exc,
            )

    if failures:
        logger.error("Completed with %s failed run(s).", failures)
        print(f"\nLog saved to: {log_file}", flush=True)
        return 1

    logger.info("All runs completed successfully.")
    print(f"\nLog saved to: {log_file}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
