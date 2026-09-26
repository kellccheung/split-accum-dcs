"""Read path_split results and combine files by basename into aggregate output."""

from __future__ import annotations

import csv
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

AGGREGATE_FOLDER_NAME = "aggregate output"
PATH_SPLIT_FILES = ("path_split01.csv", "path_split02.csv", "path_split03.csv")


def _read_split_output_path(path_split_csv: Path) -> Path:
    with path_split_csv.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    if len(rows) < 2:
        raise ValueError(f"No path data in {path_split_csv}")
    data_row = rows[1]
    raw_path = next((cell.strip() for cell in data_row if cell.strip()), "")
    if not raw_path:
        raise ValueError(f"Empty path in {path_split_csv}")
    return Path(raw_path)


def collect_split_directories(control_dir: Path) -> List[Path]:
    """Return split output directories from RESULTS/path_split01-03.csv in order."""
    results_dir = control_dir / "RESULTS"
    if not results_dir.is_dir():
        raise FileNotFoundError(f"RESULTS folder not found: {results_dir}")

    split_dirs: List[Path] = []
    for name in PATH_SPLIT_FILES:
        path_file = results_dir / name
        if not path_file.is_file():
            raise FileNotFoundError(f"Missing path split file: {path_file}")
        split_dir = _read_split_output_path(path_file)
        if not split_dir.is_dir():
            raise FileNotFoundError(f"Split output folder not found: {split_dir}")
        split_dirs.append(split_dir)
        logger.info("Resolved %s -> %s", name, split_dir)
    return split_dirs


def _group_files_by_basename(split_dirs: List[Path]) -> Dict[str, List[Path]]:
    grouped: Dict[str, List[Path]] = defaultdict(list)
    for split_dir in split_dirs:
        for file_path in sorted(split_dir.iterdir()):
            if file_path.is_file():
                grouped[file_path.name].append(file_path)
    return grouped


def _combine_csv_files(source_files: List[Path], dest_path: Path) -> None:
    if not source_files:
        return

    with dest_path.open("w", newline="", encoding="utf-8") as out_handle:
        writer = csv.writer(out_handle)
        header_written = False
        for index, source in enumerate(source_files):
            with source.open("r", newline="", encoding="utf-8-sig") as in_handle:
                reader = csv.reader(in_handle)
                try:
                    header = next(reader)
                except StopIteration:
                    logger.warning("Skipping empty file: %s", source)
                    continue

                if not header_written:
                    writer.writerow(header)
                    header_written = True

                for row in reader:
                    if row and any(cell.strip() for cell in row):
                        writer.writerow(row)

            logger.info(
                "Appended %s (%s/%s)",
                source,
                index + 1,
                len(source_files),
            )


def _combine_binary_files(source_files: List[Path], dest_path: Path) -> None:
    with dest_path.open("wb") as out_handle:
        for source in source_files:
            out_handle.write(source.read_bytes())
            logger.info("Appended %s", source)


def ensure_mimic_results(dcs_dir: Path, control_dir: Path) -> None:
    """
    If empty_*.exe did not produce RESULTS (common with license-less mimic
    binaries), write path_split01-03.csv pointing at accum_dcs_run_results.
    Real DCS writes these files itself; this is only a test fallback.
    """
    results_dir = control_dir / "RESULTS"
    missing = [
        name
        for name in PATH_SPLIT_FILES
        if not (results_dir / name).is_file()
    ]
    if not missing:
        return

    logger.warning(
        "RESULTS incomplete after exe launch (missing: %s). "
        "Writing mimic path_split files for testing.",
        ", ".join(missing),
    )
    results_dir.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(PATH_SPLIT_FILES, start=1):
        split_dir = dcs_dir / "accum_dcs_run_results" / f"split_{index:02d}"
        path_file = results_dir / name
        with path_file.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["path"])
            writer.writerow([str(split_dir.resolve())])
        logger.info("Wrote mimic %s -> %s", path_file, split_dir)


def aggregate_results(dcs_dir: Path, control_dir: Path) -> Path:
    """
    Combine files across split result folders by filename into
    {dcs_dir}/aggregate output/.
    """
    split_dirs = collect_split_directories(control_dir)
    grouped = _group_files_by_basename(split_dirs)
    if not grouped:
        raise FileNotFoundError(
            f"No result files found under split folders: {split_dirs}"
        )

    output_dir = dcs_dir / AGGREGATE_FOLDER_NAME
    output_dir.mkdir(parents=True, exist_ok=True)

    for basename, sources in sorted(grouped.items()):
        dest = output_dir / basename
        if basename.lower().endswith(".csv"):
            _combine_csv_files(sources, dest)
        else:
            _combine_binary_files(sources, dest)
        logger.info("Wrote combined file: %s", dest)

    return output_dir
