# DCS Run Automation Tool

Automates Data Conversion System (DCS) split runs from an Excel config:

1. Copy `0_split_dcs_seed` into the control folder named in the config
2. Generate `param.csv`
3. Launch `empty_1.exe`, `empty_2.exe`, and `empty_3.exe` in parallel
4. Read `RESULTS/path_split01.csv` … `path_split03.csv`
5. Combine split result files by filename into `aggregate output`

No Anaconda/Miniconda required — the tool uses a standard Python virtual environment.

## Requirements

- Windows
- Python 3.10+ available on `PATH` as `python`
- DCS run folders prepared with this layout:

```text
DCS_1/
  0_split_dcs_seed/
    empty_1.exe
    empty_2.exe
    empty_3.exe
  accum_dcs_run_results/   (or other output folders written by DCS)
```

## First-time setup

1. Copy this project folder to the target machine.
2. Double-click `setup.bat`.

This creates `.venv` and installs dependencies from `requirements.txt`.

Re-run `setup.bat` after moving the project, or when dependencies change.

## How to run

Provide an Excel config path in any of these ways:

1. **Drag and drop** the `.xlsx` file onto `run.bat`
2. **Double-click** `run.bat`, then paste/type the Excel path and press Enter
3. **Command line:**

```bat
run.bat C:\path\to\your_config.xlsx
```

Progress is printed in the console. A log file is also written under `logs\`.

## Excel config

Sample file: `config\dcs_runs.xlsx`  
Sheet name: `runs`  
One row = one DCS run.

| Column | Example | Description |
|--------|---------|-------------|
| `dcs_folder` | `DCS_1` | Folder under the project root |
| `control_folder` | `accum_dcs_control` | Destination folder created from the seed |
| `split_1_path_1` | `run_05` | `param.csv` split 1, `path_1` |
| `split_1_path_2` | `run_06` | `param.csv` split 1, `path_2` |
| `split_2_path_1` | `run_05` | Split 2, `path_1` |
| `split_2_path_2` | `run_06` | Split 2, `path_2` |
| `split_3_path_1` | `run_05` | Split 3, `path_1` |
| `split_3_path_2` | `run_06` | Split 3, `path_2` |
| `timeout_minutes` | `60` | Minutes to wait for each `empty_*.exe` in this row |

Generated `param.csv` format:

```csv
SPLIT,path_1,path_2
1,run_05,run_06
2,run_05,run_06
3,run_05,run_06
```

## What happens during a run

For each Excel row (sequentially):

1. Resolve `{project_root}\{dcs_folder}`
2. Replace `{dcs_folder}\{control_folder}` by copying `{dcs_folder}\0_split_dcs_seed`
3. Write `param.csv` into the control folder
4. Launch all `empty_*.exe` files in that control folder **in parallel**
5. Wait up to that row's `timeout_minutes` for each executable
6. Read `RESULTS\path_split01.csv` … `path_split03.csv` for output folder paths
7. Combine files that share the same filename across those split folders (header kept once, data rows appended)
8. Write combined files to `{dcs_folder}\aggregate output\`

If any executable is still running at `timeout_minutes`, steps 6–8 are skipped for that row. The process is left running, and the next Excel row starts.

Example output:

```text
DCS_1\aggregate output\pv_cf.csv
DCS_2\aggregate output\pv_cf.csv
```

## Logging

- Console: live status messages
- File: `logs\dcs_run_YYYYMMDD_HHMMSS.log`

At the end of a run, the console shows the saved log path.

## Project layout

```text
Split Accum DCS/
  setup.bat              Create .venv and install packages
  run.bat                Start a run (drag/drop or prompt for Excel)
  requirements.txt
  README.md
  config/
    dcs_runs.xlsx        Sample Excel config
  logs/                  Run logs (created automatically)
  src/
    main.py
    config_loader.py
    prepare_run.py
    launch_exe.py
    aggregate.py
  DCS_1/ ...
  DCS_2/ ...
```

## Notes

- Only `empty_*.exe` files are launched (not `control_dcs.exe`).
- Aggregation is **per DCS folder**, not across `DCS_1` + `DCS_2`.
- If a run fails, the tool logs the error and continues with the next Excel row.
- If an `empty_*.exe` is still running when `timeout_minutes` elapses, the tool logs a timeout, leaves that process running, skips aggregation for that row, and starts the next Excel row.
- `timeout_minutes` is required on every row. It must be a positive number. A blank, zero, or non-numeric value stops the run before any executable starts.
- With license-less mimic executables that do not write `RESULTS`, the tool may create temporary `path_split*.csv` files pointing at `accum_dcs_run_results\split_0N` so aggregation can still be tested. Real DCS should write those files itself.
- To move to another machine: copy the whole project folder, ensure Python is installed, then run `setup.bat` again.
