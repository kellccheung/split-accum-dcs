"""Prepare a DCS control folder from seed and write param.csv."""

from __future__ import annotations

import csv
import logging
import shutil
from pathlib import Path

from config_loader import RunConfig

logger = logging.getLogger(__name__)

SEED_FOLDER_NAME = "0_split_dcs_seed"


def prepare_control_folder(project_root: Path, run: RunConfig) -> Path:
    """
    Copy 0_split_dcs_seed to the configured control folder (overwrite if present)
    and write param.csv from the Excel row.
    """
    dcs_dir = (project_root / run.dcs_folder).resolve()
    if not dcs_dir.is_dir():
        raise FileNotFoundError(f"DCS folder not found: {dcs_dir}")

    seed_dir = dcs_dir / SEED_FOLDER_NAME
    if not seed_dir.is_dir():
        raise FileNotFoundError(f"Seed folder not found: {seed_dir}")

    control_dir = dcs_dir / run.control_folder
    if control_dir.exists():
        logger.info("Removing existing control folder: %s", control_dir)
        shutil.rmtree(control_dir)

    logger.info("Copying seed %s -> %s", seed_dir, control_dir)
    shutil.copytree(seed_dir, control_dir)

    write_param_csv(control_dir / "param.csv", run)
    return control_dir


def write_param_csv(param_path: Path, run: RunConfig) -> None:
    """Write param.csv in the existing DCS format."""
    param_path.parent.mkdir(parents=True, exist_ok=True)
    with param_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["SPLIT", "path_1", "path_2"])
        for split_id, path_1, path_2 in run.param_rows():
            writer.writerow([split_id, path_1, path_2])
    logger.info("Wrote %s", param_path)
