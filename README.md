# SSJ

**SSJ (Scontrol Show Job)** is a Python-based CLI utility that enhances the readability and interactivity of SLURM job inspection. It provides a user-friendly terminal interface to display SLURM job details with optional filtering, formatting, file inspection, and JSON export.

Ideal for HPC users who frequently monitor job metadata, logs, or scripts via `scontrol`.

## Installation

You can install this CLI tool using `uv` in two different ways:

### A. Install directly from GitHub (recommended)

```bash
uv tool install git+https://github.com/rice8y/ssj.git
```

This will fetch and install the latest version directly from the repository.

### B. Install from a local clone

1. Clone the repository:

```bash
git clone https://github.com/rice8y/ssj.git
```

2. Move into the project directory:

```bash
cd ssj
```

3. Install the package in editable mode using uv tool:

```bash
uv tool install -e .
```

This is useful if you plan to modify the code locally.

## Usage

SSJ fetches detailed SLURM job metadata using scontrol show job <jobid>, and presents the data in rich tables or JSON format. You can also inspect the job’s associated script, stdout/stderr logs, or working directory.

### Example

```bash
ssj 123456
```

This command displays a formatted table with all metadata for job `123456`.

### Options
- `-f`, `--fields <KEYS>`: Show only specified fields (partial, case-insensitive match allowed)
- `-g`, `--grep <PATTERN>`: Filter fields using a regex pattern
- `-j`, `--json`: Output raw JSON instead of a table
- `--script`: Show job script contents
- `--stdout`: Show stdout log contents
- `--stderr`: Show stderr log contents
- `--files`: List job-related file paths and their existence
- `--lines <N>`: Show only first N lines of a file (used with `--script`, `--stdout`, `--stderr`)
- `--tail`: Show last N lines instead of first N (requires `--lines`)

### Example with options

```bash
ssj 123456 --fields starttime --grep time
```

Displays job 123456 fields related to timing.

```bash
ssj 123456 --stdout --lines 20 --tail
```

Shows the last 20 lines of the job’s stdout log.

```bash
ssj 123456 --files
```

Lists script, stdout, stderr, and working directory paths associated with the job, and whether they exist.

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE).
